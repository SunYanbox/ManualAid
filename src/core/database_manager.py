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
        self._write_lock = threading.Lock()
        self._thread_local = threading.local()

        self._ensure_directory()
        self._init_tables()
        self._initialized = True

    @property
    def db_path(self) -> Path:
        return self._db_path

    def _ensure_directory(self) -> None:
        self._db_dir.mkdir(parents=True, exist_ok=True)

    def _get_connection(self) -> sqlite3.Connection:
        if not hasattr(self._thread_local, "connection") or self._thread_local.connection is None:
            conn = sqlite3.connect(str(self._db_path))
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("PRAGMA busy_timeout=5000")
            self._thread_local.connection = conn
        return self._thread_local.connection

    def _init_tables(self) -> None:
        conn = self._get_connection()
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL DEFAULT '',
                created_at  REAL NOT NULL,
                duration    REAL NOT NULL DEFAULT 0.0
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

            CREATE INDEX IF NOT EXISTS idx_tool_calls_session ON tool_calls(session_id);
            CREATE INDEX IF NOT EXISTS idx_tool_calls_func ON tool_calls(func_name);
            CREATE INDEX IF NOT EXISTS idx_file_snapshots_audit ON file_snapshots(audit_status);

            CREATE TABLE IF NOT EXISTS tool_call_summaries (
                session_id   INTEGER NOT NULL,
                func_name    TEXT NOT NULL,
                kwargs_json  TEXT NOT NULL,
                result       TEXT NOT NULL,
                timestamp    REAL NOT NULL,
                PRIMARY KEY (session_id, func_name, kwargs_json),
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            );

            CREATE INDEX IF NOT EXISTS idx_tool_call_summaries_session ON tool_call_summaries(session_id);
            """
        )
        conn.commit()

        # Phase 2 migration: add pending_content column to file_snapshots
        self._migrate_add_pending_content(conn)

        # Phase 3 migration: rename args_hash to kwargs and truncate old data
        if any(row[1] == "args_hash" for row in conn.execute("PRAGMA table_info(tool_calls)")):
            self._migrate_args_hash_to_kwargs(conn)

        # Phase 4 migration: add session_id to file_read_records
        if not any(row[1] == "session_id" for row in conn.execute("PRAGMA table_info(file_read_records)")):
            self._migrate_file_read_records_add_session(conn)

        # Ensure file_read_records index exists (for fresh databases or after migration).
        # Must run after migrations since the column may only exist after Phase 4.
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_file_read_records_session_path ON file_read_records(session_id, file_path)"
        )
        conn.commit()

    @staticmethod
    def _migrate_add_pending_content(conn: sqlite3.Connection) -> None:
        try:
            conn.execute("ALTER TABLE file_snapshots ADD COLUMN pending_content TEXT NOT NULL DEFAULT ''")
            conn.commit()
        except sqlite3.OperationalError:
            pass  # Column already exists

    @staticmethod
    def _migrate_args_hash_to_kwargs(conn: sqlite3.Connection) -> None:
        conn.execute("DELETE FROM tool_calls")
        conn.execute("ALTER TABLE tool_calls RENAME COLUMN args_hash TO kwargs")
        conn.commit()

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
        conn.commit()

    def close(self) -> None:
        if hasattr(self._thread_local, "connection") and self._thread_local.connection is not None:
            self._thread_local.connection.close()
            self._thread_local.connection = None

    # -- Unified query interface --

    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        with self._write_lock:
            conn = self._get_connection()
            cursor = conn.execute(sql, params)
            conn.commit()
            return cursor

    def fetchone(self, sql: str, params: tuple = ()) -> tuple | None:
        conn = self._get_connection()
        cursor = conn.execute(sql, params)
        return cursor.fetchone()

    def fetchall(self, sql: str, params: tuple = ()) -> list[tuple]:
        conn = self._get_connection()
        cursor = conn.execute(sql, params)
        return cursor.fetchall()

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
        with self._write_lock:
            conn = self._get_connection()
            conn.execute(
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
            conn.commit()

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
        self.execute("DELETE FROM tool_calls WHERE session_id = ?", (session_id,))
        self.execute("DELETE FROM file_snapshots WHERE session_id = ?", (session_id,))
        self.execute("DELETE FROM file_read_records WHERE session_id = ?", (session_id,))
        self.execute("DELETE FROM sessions WHERE id = ?", (session_id,))

    def get_tool_usage_ranking(self, session_id: int | None = None, limit: int = 10) -> list[tuple]:
        """Returns list of (func_name, call_count, avg_duration_ms) ordered by count DESC."""
        if session_id is not None:
            return self.fetchall(
                "SELECT func_name, COUNT(*) as cnt, AVG(duration_ms) as avg_dur "
                "FROM tool_calls WHERE session_id = ? "
                "GROUP BY func_name ORDER BY cnt DESC LIMIT ?",
                (session_id, limit),
            )
        return self.fetchall(
            "SELECT func_name, COUNT(*) as cnt, AVG(duration_ms) as avg_dur "
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
        with self._write_lock:
            conn = self._get_connection()
            conn.execute(
                "INSERT INTO tool_call_summaries "
                "(session_id, func_name, kwargs_json, result, timestamp) "
                "VALUES (?, ?, ?, ?, ?) "
                "ON CONFLICT(session_id, func_name, kwargs_json) DO UPDATE SET "
                "result = excluded.result, "
                "timestamp = excluded.timestamp",
                (session_id, func_name, kwargs_json, result, time.time()),
            )
            conn.commit()

    def get_tool_call_summaries(self, session_id: int) -> list[tuple]:
        """Get all tool call summaries for a session ordered by timestamp DESC."""
        return self.fetchall(
            "SELECT session_id, func_name, kwargs_json, result, timestamp "
            "FROM tool_call_summaries WHERE session_id = ? ORDER BY timestamp DESC",
            (session_id,),
        )
