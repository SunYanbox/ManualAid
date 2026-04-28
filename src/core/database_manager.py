import sqlite3
import threading
import time
from pathlib import Path
from typing import ClassVar

from src.constants.manual_aid import DB_FILE, MANUALAID_DIR


class DatabaseManager:
    """Thread-safe SQLite3 database manager (singleton per workspace path)."""

    _instances: ClassVar[dict[str, "DatabaseManager"]] = {}
    _instance_lock: ClassVar[threading.Lock] = threading.Lock()

    def __new__(cls, workspace_root: str) -> "DatabaseManager":
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
                args_hash    TEXT NOT NULL DEFAULT '',
                timestamp    REAL NOT NULL,
                duration_ms  REAL NOT NULL DEFAULT 0.0,
                status       TEXT NOT NULL DEFAULT 'success',
                audit_status TEXT NOT NULL DEFAULT 'none',
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            );

            CREATE TABLE IF NOT EXISTS file_read_records (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path    TEXT NOT NULL UNIQUE,
                mtime        REAL NOT NULL,
                size         INTEGER NOT NULL DEFAULT 0,
                checksum     TEXT NOT NULL DEFAULT '',
                last_read_at REAL NOT NULL,
                read_count   INTEGER NOT NULL DEFAULT 1
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
            CREATE INDEX IF NOT EXISTS idx_file_read_records_path ON file_read_records(file_path);
            CREATE INDEX IF NOT EXISTS idx_file_snapshots_audit ON file_snapshots(audit_status);
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
        args_hash: str,
        duration_ms: float = 0.0,
        status: str = "success",
        audit_status: str = "none",
    ) -> int:
        cursor = self.execute(
            "INSERT INTO tool_calls (session_id, func_name, args_hash, timestamp, duration_ms, status, audit_status) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (session_id, func_name, args_hash, time.time(), duration_ms, status, audit_status),
        )
        return cursor.lastrowid

    def update_tool_call_status(self, call_id: int, status: str, audit_status: str) -> None:
        self.execute(
            "UPDATE tool_calls SET status = ?, audit_status = ? WHERE id = ?",
            (status, audit_status, call_id),
        )

    # -- File read records --

    def record_file_read(self, file_path: str, mtime: float, size: int, checksum: str) -> None:
        with self._write_lock:
            conn = self._get_connection()
            conn.execute(
                "INSERT INTO file_read_records (file_path, mtime, size, checksum, last_read_at, read_count) "
                "VALUES (?, ?, ?, ?, ?, 1) "
                "ON CONFLICT(file_path) DO UPDATE SET "
                "mtime = excluded.mtime, "
                "size = excluded.size, "
                "checksum = excluded.checksum, "
                "last_read_at = excluded.last_read_at, "
                "read_count = read_count + 1",
                (file_path, mtime, size, checksum, time.time()),
            )
            conn.commit()

    def get_file_read_record(self, file_path: str) -> tuple | None:
        return self.fetchone(
            "SELECT id, file_path, mtime, size, checksum, last_read_at, read_count "
            "FROM file_read_records WHERE file_path = ?",
            (file_path,),
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
    ) -> int:
        cursor = self.execute(
            "INSERT INTO file_snapshots "
            "(file_path, old_hash, new_hash, diff_content, timestamp, session_id, audit_status) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (file_path, old_hash, new_hash, diff_content, time.time(), session_id, audit_status),
        )
        return cursor.lastrowid

    def update_snapshot_audit(self, snapshot_id: int, audit_status: str) -> None:
        self.execute(
            "UPDATE file_snapshots SET audit_status = ? WHERE id = ?",
            (audit_status, snapshot_id),
        )

    def get_pending_audits(self) -> list[tuple]:
        return self.fetchall(
            "SELECT id, file_path, old_hash, new_hash, diff_content, timestamp, session_id, audit_status "
            "FROM file_snapshots WHERE audit_status = 'PENDING_AUDIT'"
        )

    # -- Class-level cleanup for testing --

    @classmethod
    def reset_instances(cls) -> None:
        with cls._instance_lock:
            for instance in cls._instances.values():
                instance.close()
            cls._instances.clear()
