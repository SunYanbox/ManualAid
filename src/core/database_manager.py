import contextlib
import json
import sqlite3
import threading
import time
from pathlib import Path
from typing import ClassVar

from src.constants.manual_aid import DB_FILE, MANUALAID_DIR


class DatabaseManager:
    """Thread-safe SQLite3 database manager (singleton per workspace path)."""

    _instances: ClassVar[dict[str, DatabaseManager]] = {}
    _instance_lock: ClassVar[threading.Lock] = threading.Lock()

    def __new__(cls, workspace_root: str) -> DatabaseManager:
        with cls._instance_lock:
            if workspace_root not in cls._instances:
                instance = super().__new__(cls)
                instance._initialized = False
                cls._instances[workspace_root] = instance
        return cls._instances[workspace_root]

    def __init__(self, workspace_root: str) -> None:
        if self._initialized:
            return

        self._workspace_root = workspace_root
        self._db_dir = Path(workspace_root) / MANUALAID_DIR
        self._db_path = self._db_dir / DB_FILE
        self._lock = threading.RLock()
        self._conn: sqlite3.Connection | None = None

        self._ensure_directory()
        self._init_tables()
        self._initialized = True

    @property
    def db_path(self) -> Path:
        return self._db_path

    def _ensure_directory(self) -> None:
        self._db_dir.mkdir(parents=True, exist_ok=True)

    def _get_connection(self) -> sqlite3.Connection:
        if self._conn is None:
            conn = sqlite3.connect(
                str(self._db_path),
                isolation_level=None,
                check_same_thread=False,
            )
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("PRAGMA busy_timeout=5000")
            self._conn = conn
        return self._conn

    def _init_tables(self) -> None:
        conn = self._get_connection()
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL DEFAULT '',
                created_at  REAL NOT NULL,
                duration    REAL NOT NULL DEFAULT 0.0,
                deleted     INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS tool_calls (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id   INTEGER NOT NULL,
                func_name    TEXT NOT NULL,
                kwargs       TEXT NOT NULL DEFAULT '',
                timestamp    REAL NOT NULL,
                duration_ms  REAL NOT NULL DEFAULT 0.0,
                status       TEXT NOT NULL DEFAULT 'success',
                audit_status TEXT NOT NULL DEFAULT 'none',
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            );

            CREATE TABLE IF NOT EXISTS file_read_records (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id   INTEGER NOT NULL,
                file_path    TEXT NOT NULL,
                mtime        REAL NOT NULL,
                size         INTEGER NOT NULL DEFAULT 0,
                checksum     TEXT NOT NULL DEFAULT '',
                last_read_at REAL NOT NULL,
                read_count   INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY (session_id) REFERENCES sessions(id),
                UNIQUE(session_id, file_path)
            );

            CREATE TABLE IF NOT EXISTS file_snapshots (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path    TEXT NOT NULL,
                old_hash     TEXT,
                new_hash     TEXT NOT NULL,
                diff_content TEXT NOT NULL DEFAULT '',
                timestamp    REAL NOT NULL,
                session_id   INTEGER,
                audit_status TEXT NOT NULL DEFAULT 'PENDING_AUDIT',
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            );

            CREATE TABLE IF NOT EXISTS tool_call_summaries (
                session_id   INTEGER NOT NULL,
                func_name    TEXT NOT NULL,
                kwargs_json  TEXT NOT NULL,
                result       TEXT NOT NULL,
                timestamp    REAL NOT NULL,
                PRIMARY KEY (session_id, func_name, kwargs_json),
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            );

            CREATE TABLE IF NOT EXISTS config (
                key          TEXT PRIMARY KEY,
                value        TEXT NOT NULL,
                category     TEXT NOT NULL DEFAULT 'general',
                updated_at   REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS shell_audit (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                command      TEXT NOT NULL,
                description  TEXT NOT NULL DEFAULT '',
                timestamp    REAL NOT NULL,
                session_id   INTEGER,
                audit_status TEXT NOT NULL DEFAULT 'PENDING_AUDIT',
                output       TEXT NOT NULL DEFAULT '',
                exit_code    INTEGER,
                executed_at  REAL,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            );
            """
        )

        # Phase 2 migration: add pending_content column to file_snapshots
        self._migrate_add_pending_content(conn)

        # Phase 3 migration: rename args_hash to kwargs and truncate old data
        if any(row[1] == "args_hash" for row in conn.execute("PRAGMA table_info(tool_calls)")):
            self._migrate_args_hash_to_kwargs(conn)

        # Phase 4 migration: add session_id to file_read_records
        if not any(row[1] == "session_id" for row in conn.execute("PRAGMA table_info(file_read_records)")):
            self._migrate_file_read_records_add_session(conn)

        # Phase 5 migration: add deleted column to sessions
        if not any(row[1] == "deleted" for row in conn.execute("PRAGMA table_info(sessions)")):
            conn.execute("ALTER TABLE sessions ADD COLUMN deleted INTEGER NOT NULL DEFAULT 0")

        # Phase 6 migration: add config table
        if not any(row[1] == "key" for row in conn.execute("PRAGMA table_info(config)")):
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS config (
                    key          TEXT PRIMARY KEY,
                    value        TEXT NOT NULL,
                    category     TEXT NOT NULL DEFAULT 'general',
                    updated_at   REAL NOT NULL
                )
                """
            )

        # Create all indexes after migrations so they apply to both
        # fresh databases and those upgraded from older schemas.
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tool_calls_session ON tool_calls(session_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tool_calls_func ON tool_calls(func_name)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_file_snapshots_audit ON file_snapshots(audit_status)")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_file_read_records_session_path ON file_read_records(session_id, file_path)"
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tool_call_summaries_session ON tool_call_summaries(session_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_shell_audit_status ON shell_audit(audit_status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_shell_audit_session ON shell_audit(session_id)")

    @staticmethod
    def _migrate_add_pending_content(conn: sqlite3.Connection) -> None:
        with contextlib.suppress(sqlite3.OperationalError):
            conn.execute("ALTER TABLE file_snapshots ADD COLUMN pending_content TEXT NOT NULL DEFAULT ''")

    @staticmethod
    def _migrate_args_hash_to_kwargs(conn: sqlite3.Connection) -> None:
        conn.execute("DELETE FROM tool_calls")
        conn.execute("ALTER TABLE tool_calls RENAME COLUMN args_hash TO kwargs")

    @staticmethod
    def _migrate_file_read_records_add_session(conn: sqlite3.Connection) -> None:
        conn.executescript(
            """
            DROP TABLE IF EXISTS file_read_records;

            CREATE TABLE file_read_records (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id   INTEGER NOT NULL,
                file_path    TEXT NOT NULL,
                mtime        REAL NOT NULL,
                size         INTEGER NOT NULL DEFAULT 0,
                checksum     TEXT NOT NULL DEFAULT '',
                last_read_at REAL NOT NULL,
                read_count   INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY (session_id) REFERENCES sessions(id),
                UNIQUE(session_id, file_path)
            );

            CREATE INDEX IF NOT EXISTS idx_file_read_records_session_path ON file_read_records(session_id, file_path);
            """
        )

    def close(self) -> None:
        with self._lock:
            if self._conn is not None:
                self._conn.close()
                self._conn = None

    # -- Unified query interface --

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        with self._lock:
            return self._get_connection().execute(sql, params)

    def fetchone(self, sql: str, params: tuple = ()) -> tuple | None:
        with self._lock:
            return self._get_connection().execute(sql, params).fetchone()

    def fetchall(self, sql: str, params: tuple = ()) -> list[tuple]:
        with self._lock:
            return self._get_connection().execute(sql, params).fetchall()

    # -- Session lifecycle --

    def create_session(self, name: str = "") -> int:
        cursor = self.execute(
            "INSERT INTO sessions (name, created_at) VALUES (?, ?)",
            (name, time.time()),
        )
        return cursor.lastrowid

    def close_session(self, session_id: int) -> None:
        row = self.fetchone("SELECT created_at FROM sessions WHERE id = ?", (session_id,))
        if row:
            duration = time.time() - row[0]
            self.execute(
                "UPDATE sessions SET duration = ? WHERE id = ?",
                (duration, session_id),
            )
            # Mark empty sessions as deleted so they can be cleaned up later
            if self.is_session_orphaned(session_id):
                self.mark_session_deleted(session_id)

    def update_session_duration(self, session_id: int) -> None:
        """Persist current elapsed duration without closing the session.

        Used by the periodic heartbeat so that abnormal termination (window
        close, Ctrl+C, SIGKILL) loses at most the heartbeat interval's worth
        of session duration data.
        """
        row = self.fetchone("SELECT created_at FROM sessions WHERE id = ?", (session_id,))
        if row:
            duration = time.time() - row[0]
            self.execute(
                "UPDATE sessions SET duration = ? WHERE id = ?",
                (duration, session_id),
            )

    def mark_session_deleted(self, session_id: int) -> None:
        """Set the deleted flag on a session.

        设置会话上的删除标志"""
        self.execute("UPDATE sessions SET deleted = 1 WHERE id = ?", (session_id,))

    def restore_session_deleted_flag(self, session_id: int) -> None:
        """Restore the deleted flag (set it back to 0) for an active session.

        恢复删除标志(将其设回 0)为一个活跃会话
        """
        self.execute("UPDATE sessions SET deleted = 0 WHERE id = ?", (session_id,))

    def get_sessions_with_deleted_flag(self) -> list[int]:
        """Return IDs of all sessions with the deleted flag set.

        返回所有设置了删除标志的会话的 ID
        """
        rows = self.fetchall("SELECT id FROM sessions WHERE deleted = 1")
        return [r[0] for r in rows]

    def is_session_orphaned(self, session_id: int) -> bool:
        """Check if a session has no associated data in any related table.

        检查一个会话是否在任何相关表中都没有关联数据
        """
        tables = ["tool_calls", "file_read_records", "file_snapshots", "tool_call_summaries", "shell_audit"]
        for table in tables:
            row = self.fetchone(
                f"SELECT COUNT(*) FROM {table} WHERE session_id = ?",
                (session_id,),
            )
            if row and row[0] > 0:
                return False
        return True

    def delete_session_async(self, session_id: int) -> None:
        """异步轮询删除会话

        设置删除标志,然后每 10 秒轮询一次(共重试 3 次)
        如果标志被心跳恢复,则取消删除操作
        否则在第三次轮询后执行实际删除
        """
        self.mark_session_deleted(session_id)

        def _poll() -> None:
            for _ in range(3):
                time.sleep(10)
                row = self.fetchone("SELECT deleted FROM sessions WHERE id = ?", (session_id,))
                if row and row[0] == 0:
                    return  # Flag was restored, cancel deletion / 标志已恢复,取消删除
            # 三次轮询已过,标志仍被设置——执行删除
            # Three polls passed, flag still set -- execute deletion
            self.delete_session(session_id)

        thread = threading.Thread(target=_poll, daemon=True)
        thread.start()

    # -- Tool call logging --

    def log_tool_call(
        self,
        session_id: int,
        func_name: str,
        kwargs: str,
        duration_ms: float = 0.0,
        status: str = "success",
        audit_status: str = "none",
    ) -> int:
        cursor = self.execute(
            "INSERT INTO tool_calls (session_id, func_name, kwargs, timestamp, duration_ms, status, audit_status) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (session_id, func_name, kwargs, time.time(), duration_ms, status, audit_status),
        )
        return cursor.lastrowid

    def update_tool_call_status(self, call_id: int, status: str, audit_status: str) -> None:
        self.execute(
            "UPDATE tool_calls SET status = ?, audit_status = ? WHERE id = ?",
            (status, audit_status, call_id),
        )

    # -- File read records --

    def record_file_read(self, session_id: int, file_path: str, mtime: float, size: int, checksum: str) -> None:
        with self._lock:
            self._get_connection().execute(
                "INSERT INTO file_read_records "
                "(session_id, file_path, mtime, size, checksum, last_read_at, read_count) "
                "VALUES (?, ?, ?, ?, ?, ?, 1) "
                "ON CONFLICT(session_id, file_path) DO UPDATE SET "
                "mtime = excluded.mtime, "
                "size = excluded.size, "
                "checksum = excluded.checksum, "
                "last_read_at = excluded.last_read_at, "
                "read_count = read_count + 1",
                (session_id, file_path, mtime, size, checksum, time.time()),
            )

    def get_file_read_record(self, session_id: int, file_path: str) -> tuple | None:
        return self.fetchone(
            "SELECT id, session_id, file_path, mtime, size, checksum, last_read_at, read_count "
            "FROM file_read_records WHERE session_id = ? AND file_path = ?",
            (session_id, file_path),
        )

    # -- File snapshots --

    def record_file_snapshot(
        self,
        file_path: str,
        old_hash: str | None,
        new_hash: str,
        diff_content: str,
        audit_status: str = "PENDING_AUDIT",
        session_id: int | None = None,
        pending_content: str = "",
    ) -> int:
        cursor = self.execute(
            "INSERT INTO file_snapshots "
            "(file_path, old_hash, new_hash, diff_content, timestamp, session_id, audit_status, pending_content) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (file_path, old_hash, new_hash, diff_content, time.time(), session_id, audit_status, pending_content),
        )
        return cursor.lastrowid

    def update_snapshot_audit(self, snapshot_id: int, audit_status: str) -> None:
        self.execute(
            "UPDATE file_snapshots SET audit_status = ? WHERE id = ?",
            (audit_status, snapshot_id),
        )

    def get_pending_audits(self) -> list[tuple]:
        return self.fetchall(
            "SELECT id, file_path, old_hash, new_hash, diff_content, timestamp, session_id, audit_status"
            " FROM file_snapshots WHERE audit_status = 'PENDING_AUDIT'"
        )

    def get_snapshot_by_id(self, snapshot_id: int) -> tuple | None:
        return self.fetchone(
            "SELECT id, file_path, old_hash, new_hash, diff_content, timestamp, session_id, audit_status,"
            " pending_content FROM file_snapshots WHERE id = ?",
            (snapshot_id,),
        )

    def get_snapshots_by_audit_status(self, status: str) -> list[tuple]:
        return self.fetchall(
            "SELECT id, file_path, old_hash, new_hash, diff_content, timestamp, session_id, audit_status,"
            " pending_content FROM file_snapshots WHERE audit_status = ?",
            (status,),
        )

    # -- Shell command audit --

    def record_shell_command(
        self,
        command: str,
        description: str = "",
        session_id: int | None = None,
    ) -> int:
        """记录一条待审核的 Shell 命令.

        Args:
            command: Shell 命令内容
            description: 命令描述
            session_id: 会话 ID

        Returns:
            新记录的 ID
        """
        cursor = self.execute(
            "INSERT INTO shell_audit (command, description, timestamp, session_id, audit_status) "
            "VALUES (?, ?, ?, ?, 'PENDING_AUDIT')",
            (command, description, time.time(), session_id),
        )
        return cursor.lastrowid

    def update_shell_audit(
        self,
        shell_id: int,
        audit_status: str,
        output: str = "",
        exit_code: int | None = None,
    ) -> None:
        """更新 Shell 命令审核状态及执行结果.

        Args:
            shell_id: 记录 ID
            audit_status: 审核状态 (APPROVED/REJECTED)
            output: 命令执行输出
            exit_code: 命令退出码
        """
        if output or exit_code is not None:
            self.execute(
                "UPDATE shell_audit SET audit_status = ?, output = ?, exit_code = ?, executed_at = ? WHERE id = ?",
                (audit_status, output, exit_code, time.time(), shell_id),
            )
        else:
            self.execute(
                "UPDATE shell_audit SET audit_status = ? WHERE id = ?",
                (audit_status, shell_id),
            )

    def get_shell_pending_audits(self) -> list[tuple]:
        """获取所有待审核的 Shell 命令.

        Returns:
            待审核记录列表 (id, command, description, timestamp, session_id, audit_status)
        """
        return self.fetchall(
            "SELECT id, command, description, timestamp, session_id, audit_status"
            " FROM shell_audit WHERE audit_status = 'PENDING_AUDIT'"
        )

    def get_shell_by_id(self, shell_id: int) -> tuple | None:
        """根据 ID 获取 Shell 命令审核记录.

        Args:
            shell_id: 记录 ID

        Returns:
            记录元组或 None
        """
        return self.fetchone(
            "SELECT id, command, description, timestamp, session_id,"
            " audit_status, output, exit_code, executed_at"
            " FROM shell_audit WHERE id = ?",
            (shell_id,),
        )

    def get_shell_completed(self, limit: int = 200) -> list[tuple]:
        """获取所有已完成的 Shell 命令(已批准/已拒绝),按执行时间倒序.

        Args:
            limit: 最大返回条数

        Returns:
            已完成记录列表, 每条含 (id, command, description, timestamp,
            session_id, audit_status, output, exit_code, executed_at)
        """
        return self.fetchall(
            "SELECT id, command, description, timestamp, session_id,"
            " audit_status, output, exit_code, executed_at"
            " FROM shell_audit WHERE audit_status != 'PENDING_AUDIT'"
            " ORDER BY COALESCE(executed_at, timestamp) DESC LIMIT ?",
            (limit,),
        )

    # -- Session statistics and management --

    def get_session_summary(self, session_id: int) -> dict:
        """Aggregated stats for a single session."""
        session = self.fetchone(
            "SELECT id, name, created_at, duration FROM sessions WHERE id = ?",
            (session_id,),
        )
        if not session:
            return {}

        total = self.fetchone(
            "SELECT COUNT(*), SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END), "
            "SUM(CASE WHEN status = 'error' THEN 1 ELSE 0 END) "
            "FROM tool_calls WHERE session_id = ?",
            (session_id,),
        )
        total_calls, success_count, fail_count = total or (0, 0, 0)

        return {
            "id": session[0],
            "name": session[1],
            "created_at": session[2],
            "duration": session[3],
            "total_calls": total_calls or 0,
            "success_count": success_count or 0,
            "fail_count": fail_count or 0,
            "success_rate": (success_count / total_calls * 100) if total_calls else 0.0,
        }

    def get_all_sessions(self) -> list[tuple]:
        """All sessions ordered by created_at descending."""
        return self.fetchall("SELECT id, name, created_at, duration FROM sessions ORDER BY created_at DESC")

    def rename_session(self, session_id: int, name: str) -> None:
        self.execute("UPDATE sessions SET name = ? WHERE id = ?", (name, session_id))

    def delete_session(self, session_id: int) -> None:
        with self._lock:
            conn = self._get_connection()
            conn.execute("BEGIN IMMEDIATE")
            try:
                conn.execute("DELETE FROM tool_calls WHERE session_id = ?", (session_id,))
                conn.execute("DELETE FROM file_snapshots WHERE session_id = ?", (session_id,))
                conn.execute("DELETE FROM file_read_records WHERE session_id = ?", (session_id,))
                conn.execute("DELETE FROM shell_audit WHERE session_id = ?", (session_id,))
                conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise

    def get_tool_usage_ranking(self, session_id: int | None = None, limit: int = 10) -> list[tuple]:
        """Returns list of (func_name, call_count, avg_duration_ms, total_duration_ms) ordered by count DESC."""
        if session_id is not None:
            return self.fetchall(
                "SELECT func_name, COUNT(*) as cnt, AVG(duration_ms) as avg_dur, SUM(duration_ms) as total_dur "
                "FROM tool_calls WHERE session_id = ? "
                "GROUP BY func_name ORDER BY cnt DESC LIMIT ?",
                (session_id, limit),
            )
        return self.fetchall(
            "SELECT func_name, COUNT(*) as cnt, AVG(duration_ms) as avg_dur, SUM(duration_ms) as total_dur "
            "FROM tool_calls "
            "GROUP BY func_name ORDER BY cnt DESC LIMIT ?",
            (limit,),
        )

    # -- Class-level cleanup for testing --

    @classmethod
    def reset_instances(cls) -> None:
        with cls._instance_lock:
            for instance in cls._instances.values():
                instance.close()
            cls._instances.clear()

    # -- Tool call summaries --

    def record_tool_call_summary(
        self,
        session_id: int,
        func_name: str,
        kwargs_json: str,
        result: str,
    ) -> None:
        with self._lock:
            self._get_connection().execute(
                "INSERT INTO tool_call_summaries "
                "(session_id, func_name, kwargs_json, result, timestamp) "
                "VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(session_id, func_name, kwargs_json) DO UPDATE SET "
                "result = excluded.result, "
                "timestamp = excluded.timestamp",
                (session_id, func_name, kwargs_json, result, time.time()),
            )

    def get_tool_call_summaries(self, session_id: int) -> list[tuple]:
        """Get all tool call summaries for a session ordered by timestamp DESC."""
        return self.fetchall(
            "SELECT session_id, func_name, kwargs_json, result, timestamp "
            "FROM tool_call_summaries WHERE session_id = ? ORDER BY timestamp DESC",
            (session_id,),
        )

    # -- Configuration management --

    def get_config(self, key: str, default: str | None = None) -> str | None:
        """Get a configuration value by key.

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        row = self.fetchone("SELECT value FROM config WHERE key = ?", (key,))
        return row[0] if row else default

    def set_config(self, key: str, value: str, category: str = "general") -> None:
        """Set a configuration value.

        Args:
            key: Configuration key
            value: Configuration value
            category: Configuration category (general, skill, env, etc.)
        """
        self.execute(
            "INSERT INTO config (key, value, category, updated_at) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value, category = excluded.category, "
            "updated_at = excluded.updated_at",
            (key, value, category, time.time()),
        )

    def delete_config(self, key: str) -> None:
        """Delete a configuration value.

        Args:
            key: Configuration key
        """
        self.execute("DELETE FROM config WHERE key = ?", (key,))

    def get_all_config(self, category: str | None = None) -> list[tuple]:
        """Get all configuration values, optionally filtered by category.

        Args:
            category: Optional category filter

        Returns:
            List of (key, value, category, updated_at) tuples
        """
        if category:
            return self.fetchall(
                "SELECT key, value, category, updated_at FROM config WHERE category = ? ORDER BY key",
                (category,),
            )
        return self.fetchall("SELECT key, value, category, updated_at FROM config ORDER BY category, key")

    def get_config_by_prefix(self, prefix: str) -> dict[str, str]:
        """Get all configuration values with a given key prefix.

        Args:
            prefix: Key prefix to filter by

        Returns:
            Dictionary of key-value pairs
        """
        rows = self.fetchall(
            "SELECT key, value FROM config WHERE key LIKE ? ORDER BY key",
            (f"{prefix}%",),
        )
        return {row[0]: row[1] for row in rows}

    # -- Skill configuration shortcuts --

    def get_disabled_skills(self) -> set[str]:
        """Get the set of disabled skill names.

        Returns:
            Set of disabled skill names
        """
        value = self.get_config("skills.disabled")
        if not value:
            return set()
        import json

        try:
            return set(json.loads(value))
        except json.JSONDecodeError, TypeError:
            return set()

    def set_disabled_skills(self, names) -> None:
        """Set the disabled skill names.

        Args:
            names: Collection of skill names to disable (set, list, or tuple)
        """
        self.set_config("skills.disabled", json.dumps(sorted(set(names))), category="skill")
