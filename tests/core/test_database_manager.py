import time
from pathlib import Path

import pytest

from src.core.database_manager import DatabaseManager


@pytest.fixture(autouse=True)
def isolate_database_manager():
    DatabaseManager.reset_instances()
    yield
    DatabaseManager.reset_instances()


@pytest.fixture
def workspace_root(tmp_path: Path) -> str:
    return str(tmp_path / "workspace")


@pytest.fixture
def db(workspace_root: str) -> DatabaseManager:
    root = Path(workspace_root)
    root.mkdir(parents=True, exist_ok=True)
    return DatabaseManager(workspace_root)


class TestSingleton:
    def test_same_path_returns_same_instance(self, workspace_root: str):
        root = Path(workspace_root)
        root.mkdir(parents=True, exist_ok=True)
        db1 = DatabaseManager(workspace_root)
        db2 = DatabaseManager(workspace_root)
        assert db1 is db2

    def test_different_paths_return_different_instances(self, tmp_path: Path):
        root1 = tmp_path / "ws1"
        root2 = tmp_path / "ws2"
        root1.mkdir()
        root2.mkdir()
        db1 = DatabaseManager(str(root1))
        db2 = DatabaseManager(str(root2))
        assert db1 is not db2


class TestDirectoryAndDbCreation:
    def test_directory_created_on_init(self, db: DatabaseManager, workspace_root: str):
        assert (Path(workspace_root) / ".ManualAid").is_dir()

    def test_db_file_exists_after_init(self, db: DatabaseManager):
        assert db.db_path.is_file()

    def test_wal_mode_enabled(self, db: DatabaseManager):
        row = db.fetchone("PRAGMA journal_mode")
        assert row is not None
        assert row[0] == "wal"


class TestTableCreation:
    def test_sessions_table_exists(self, db: DatabaseManager):
        rows = db.fetchall("SELECT name FROM sqlite_master WHERE type='table' AND name='sessions'")
        assert len(rows) == 1

    def test_tool_calls_table_exists(self, db: DatabaseManager):
        rows = db.fetchall("SELECT name FROM sqlite_master WHERE type='table' AND name='tool_calls'")
        assert len(rows) == 1

    def test_file_read_records_table_exists(self, db: DatabaseManager):
        rows = db.fetchall("SELECT name FROM sqlite_master WHERE type='table' AND name='file_read_records'")
        assert len(rows) == 1

    def test_file_snapshots_table_exists(self, db: DatabaseManager):
        rows = db.fetchall("SELECT name FROM sqlite_master WHERE type='table' AND name='file_snapshots'")
        assert len(rows) == 1


class TestSessionLifecycle:
    def test_create_session(self, db: DatabaseManager):
        session_id = db.create_session(name="test_session")
        assert isinstance(session_id, int)
        assert session_id > 0

    def test_close_session_updates_duration(self, db: DatabaseManager):
        session_id = db.create_session(name="test_session")
        time.sleep(0.05)
        db.close_session(session_id)

        row = db.fetchone("SELECT duration FROM sessions WHERE id = ?", (session_id,))
        assert row is not None
        assert row[0] > 0

    def test_close_nonexistent_session(self, db: DatabaseManager):
        db.close_session(9999)


class TestToolCallLogging:
    def test_log_tool_call(self, db: DatabaseManager):
        session_id = db.create_session()
        call_id = db.log_tool_call(session_id, "read", "abc123", duration_ms=50.0, status="success")
        assert isinstance(call_id, int)
        assert call_id > 0

    def test_log_tool_call_stored_correctly(self, db: DatabaseManager):
        session_id = db.create_session()
        db.log_tool_call(session_id, "write", "def456", duration_ms=120.0, status="error", audit_status="none")

        row = db.fetchone(
            "SELECT func_name, args_hash, duration_ms, status FROM tool_calls WHERE session_id = ?",
            (session_id,),
        )
        assert row is not None
        assert row[0] == "write"
        assert row[1] == "def456"
        assert row[2] == 120.0
        assert row[3] == "error"

    def test_update_tool_call_status(self, db: DatabaseManager):
        session_id = db.create_session()
        call_id = db.log_tool_call(session_id, "edit", "xyz")

        db.update_tool_call_status(call_id, "error", "PENDING_AUDIT")

        row = db.fetchone("SELECT status, audit_status FROM tool_calls WHERE id = ?", (call_id,))
        assert row is not None
        assert row[0] == "error"
        assert row[1] == "PENDING_AUDIT"


class TestFileReadRecords:
    def test_record_file_read(self, db: DatabaseManager):
        db.record_file_read("src/main.py", 1234567890.5, 1024, "abc123hash")

        row = db.get_file_read_record("src/main.py")
        assert row is not None
        assert row[2] == 1234567890.5
        assert row[3] == 1024
        assert row[4] == "abc123hash"

    def test_record_file_read_upsert(self, db: DatabaseManager):
        db.record_file_read("src/main.py", 1000.0, 100, "hash1")
        db.record_file_read("src/main.py", 2000.0, 200, "hash2")

        row = db.get_file_read_record("src/main.py")
        assert row is not None
        assert row[2] == 2000.0
        assert row[3] == 200
        assert row[4] == "hash2"
        assert row[6] == 2

    def test_get_nonexistent_read_record(self, db: DatabaseManager):
        row = db.get_file_read_record("nonexistent.py")
        assert row is None


class TestFileSnapshots:
    def test_record_file_snapshot(self, db: DatabaseManager):
        snapshot_id = db.record_file_snapshot(
            "src/main.py", "old_hash", "new_hash", "--- a/src/main.py\n+++ b/src/main.py\n"
        )
        assert isinstance(snapshot_id, int)
        assert snapshot_id > 0

    def test_snapshot_stored_correctly(self, db: DatabaseManager):
        session_id = db.create_session()
        db.record_file_snapshot(
            "src/main.py", None, "new_hash", "diff content", audit_status="PENDING_AUDIT", session_id=session_id
        )

        rows = db.fetchall("SELECT file_path, old_hash, new_hash, diff_content, audit_status FROM file_snapshots")
        assert len(rows) == 1
        assert rows[0][0] == "src/main.py"
        assert rows[0][1] is None
        assert rows[0][2] == "new_hash"
        assert rows[0][3] == "diff content"
        assert rows[0][4] == "PENDING_AUDIT"

    def test_update_snapshot_audit(self, db: DatabaseManager):
        snapshot_id = db.record_file_snapshot("src/main.py", "old", "new", "diff")

        db.update_snapshot_audit(snapshot_id, "APPROVED")

        row = db.fetchone("SELECT audit_status FROM file_snapshots WHERE id = ?", (snapshot_id,))
        assert row is not None
        assert row[0] == "APPROVED"

    def test_get_pending_audits(self, db: DatabaseManager):
        db.record_file_snapshot("a.py", None, "h1", "diff1")
        db.record_file_snapshot("b.py", "h0", "h2", "diff2")
        db.record_file_snapshot("c.py", "h0", "h3", "diff3", audit_status="APPROVED")

        pending = db.get_pending_audits()
        assert len(pending) == 2

    def test_snapshot_with_session_id(self, db: DatabaseManager):
        session_id = db.create_session()
        db.record_file_snapshot("src/main.py", "old", "new", "diff", session_id=session_id)

        row = db.fetchone("SELECT session_id FROM file_snapshots WHERE file_path = 'src/main.py'")
        assert row is not None
        assert row[0] == session_id


class TestPendingContentMigration:
    def test_pending_content_column_exists(self, db: DatabaseManager):
        cols = db.fetchall("PRAGMA table_info(file_snapshots)")
        col_names = [c[1] for c in cols]
        assert "pending_content" in col_names

    def test_pending_content_default_empty(self, db: DatabaseManager):
        snapshot_id = db.record_file_snapshot("src/main.py", "old", "new", "diff")
        row = db.fetchone("SELECT pending_content FROM file_snapshots WHERE id = ?", (snapshot_id,))
        assert row is not None
        assert row[0] == ""

    def test_pending_content_stored(self, db: DatabaseManager):
        session_id = db.create_session()
        db.execute(
            "UPDATE file_snapshots SET pending_content = ? WHERE id = ?",
            ("new file content", 1),
        )
        # Use record_file_snapshot with explicit pending_content via direct SQL
        # since the method currently doesn't have pending_content param
        snapshot_id = db.record_file_snapshot(
            "src/main.py",
            "old_hash",
            "new_hash",
            "diff_content",
            audit_status="PENDING_AUDIT",
            session_id=session_id,
        )
        db.execute(
            "UPDATE file_snapshots SET pending_content = ? WHERE id = ?",
            ("pending content here", snapshot_id),
        )
        row = db.fetchone("SELECT pending_content FROM file_snapshots WHERE id = ?", (snapshot_id,))
        assert row is not None
        assert row[0] == "pending content here"


class TestGetSnapshotById:
    def test_get_existing_snapshot(self, db: DatabaseManager):
        session_id = db.create_session()
        db.record_file_snapshot(
            "src/main.py",
            "old_hash",
            "new_hash",
            "diff_content",
            audit_status="PENDING_AUDIT",
            session_id=session_id,
        )
        # Set pending_content directly
        db.execute(
            "UPDATE file_snapshots SET pending_content = ? WHERE id = ?",
            ("pending content", 1),
        )

        row = db.get_snapshot_by_id(1)
        assert row is not None
        assert row[1] == "src/main.py"
        assert row[8] == "pending content"

    def test_get_nonexistent_snapshot(self, db: DatabaseManager):
        row = db.get_snapshot_by_id(9999)
        assert row is None


class TestGetSnapshotsByAuditStatus:
    def test_filter_by_status(self, db: DatabaseManager):
        db.record_file_snapshot("a.py", None, "h1", "diff1")
        db.record_file_snapshot("b.py", "h0", "h2", "diff2", audit_status="APPROVED")
        db.record_file_snapshot("c.py", "h0", "h3", "diff3", audit_status="REJECTED")

        pending = db.get_snapshots_by_audit_status("PENDING_AUDIT")
        approved = db.get_snapshots_by_audit_status("APPROVED")
        rejected = db.get_snapshots_by_audit_status("REJECTED")

        assert len(pending) == 1
        assert pending[0][1] == "a.py"
        assert len(approved) == 1
        assert approved[0][1] == "b.py"
        assert len(rejected) == 1
        assert rejected[0][1] == "c.py"

    def test_no_matching_status(self, db: DatabaseManager):
        rows = db.get_snapshots_by_audit_status("NONEXISTENT_STATUS")
        assert len(rows) == 0


class TestThreadSafety:
    def test_concurrent_writes(self, db: DatabaseManager):
        import threading

        errors = []

        def write_session(name):
            try:
                db.create_session(name=name)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=write_session, args=(f"thread_{i}",)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        rows = db.fetchall("SELECT COUNT(*) FROM sessions")
        assert rows[0][0] == 5


class TestClose:
    def test_close_and_reopen(self, workspace_root: str):
        root = Path(workspace_root)
        root.mkdir(parents=True, exist_ok=True)
        db1 = DatabaseManager(workspace_root)
        db1.create_session("first")
        db1.close()

        db2 = DatabaseManager(workspace_root)
        rows = db2.fetchall("SELECT COUNT(*) FROM sessions")
        assert rows[0][0] == 1


class TestSessionSummary:
    def test_summary_returns_empty_for_nonexistent_session(self, db: DatabaseManager):
        summary = db.get_session_summary(9999)
        assert summary == {}

    def test_summary_with_no_tool_calls(self, db: DatabaseManager):
        session_id = db.create_session(name="empty_session")
        summary = db.get_session_summary(session_id)
        assert summary["name"] == "empty_session"
        assert summary["total_calls"] == 0
        assert summary["success_count"] == 0
        assert summary["fail_count"] == 0
        assert summary["success_rate"] == 0.0

    def test_summary_with_tool_calls(self, db: DatabaseManager):
        session_id = db.create_session(name="test")
        db.log_tool_call(session_id, "read", "hash1", status="success")
        db.log_tool_call(session_id, "write", "hash2", status="success")
        db.log_tool_call(session_id, "edit", "hash3", status="error")

        summary = db.get_session_summary(session_id)
        assert summary["total_calls"] == 3
        assert summary["success_count"] == 2
        assert summary["fail_count"] == 1
        assert summary["success_rate"] == pytest.approx(66.6667, rel=0.01)

    def test_summary_duration(self, db: DatabaseManager):
        session_id = db.create_session(name="dur_test")
        time.sleep(0.05)
        db.close_session(session_id)
        summary = db.get_session_summary(session_id)
        assert summary["duration"] > 0


class TestAllSessions:
    def test_get_all_sessions_empty(self, db: DatabaseManager):
        sessions = db.get_all_sessions()
        assert len(sessions) == 0

    def test_get_all_sessions_ordering(self, db: DatabaseManager):
        id1 = db.create_session(name="first")
        id2 = db.create_session(name="second")
        id3 = db.create_session(name="third")

        sessions = db.get_all_sessions()
        assert len(sessions) == 3
        # Most recent first
        assert sessions[0][0] == id3
        assert sessions[1][0] == id2
        assert sessions[2][0] == id1

    def test_get_all_sessions_returns_columns(self, db: DatabaseManager):
        db.create_session(name="check_columns")
        sessions = db.get_all_sessions()
        row = sessions[0]
        assert len(row) == 4  # id, name, created_at, duration


class TestRenameSession:
    def test_rename_session(self, db: DatabaseManager):
        session_id = db.create_session(name="original")
        db.rename_session(session_id, "renamed")
        row = db.fetchone("SELECT name FROM sessions WHERE id = ?", (session_id,))
        assert row is not None
        assert row[0] == "renamed"

    def test_rename_nonexistent_session(self, db: DatabaseManager):
        db.rename_session(9999, "ghost")  # Should not raise


class TestDeleteSession:
    def test_delete_session_removes_session(self, db: DatabaseManager):
        session_id = db.create_session(name="to_delete")
        db.delete_session(session_id)
        row = db.fetchone("SELECT id FROM sessions WHERE id = ?", (session_id,))
        assert row is None

    def test_delete_session_removes_tool_calls(self, db: DatabaseManager):
        session_id = db.create_session()
        db.log_tool_call(session_id, "read", "hash1")
        db.log_tool_call(session_id, "write", "hash2")

        # Verify tool calls exist
        rows = db.fetchall("SELECT COUNT(*) FROM tool_calls WHERE session_id = ?", (session_id,))
        assert rows[0][0] == 2

        db.delete_session(session_id)

        rows = db.fetchall("SELECT COUNT(*) FROM tool_calls WHERE session_id = ?", (session_id,))
        assert rows[0][0] == 0

    def test_delete_session_removes_snapshots(self, db: DatabaseManager):
        session_id = db.create_session()
        db.record_file_snapshot("a.py", "old", "new", "diff", session_id=session_id)

        rows = db.fetchall("SELECT COUNT(*) FROM file_snapshots WHERE session_id = ?", (session_id,))
        assert rows[0][0] == 1

        db.delete_session(session_id)

        rows = db.fetchall("SELECT COUNT(*) FROM file_snapshots WHERE session_id = ?", (session_id,))
        assert rows[0][0] == 0

    def test_delete_nonexistent_session(self, db: DatabaseManager):
        db.delete_session(9999)  # Should not raise

    def test_delete_session_keeps_other_sessions(self, db: DatabaseManager):
        sid1 = db.create_session()
        sid2 = db.create_session()
        db.log_tool_call(sid1, "read", "h1")
        db.log_tool_call(sid2, "write", "h2")

        db.delete_session(sid1)

        remaining = db.fetchall("SELECT id FROM sessions")
        assert len(remaining) == 1
        assert remaining[0][0] == sid2


class TestToolUsageRanking:
    def test_ranking_empty(self, db: DatabaseManager):
        ranking = db.get_tool_usage_ranking()
        assert len(ranking) == 0

    def test_ranking_global(self, db: DatabaseManager):
        sid1 = db.create_session()
        sid2 = db.create_session()

        # Session 1: 3 reads, 2 writes
        for _ in range(3):
            db.log_tool_call(sid1, "read", "h", duration_ms=10.0)
        for _ in range(2):
            db.log_tool_call(sid1, "write", "h", duration_ms=20.0)

        # Session 2: 1 read, 1 glob
        db.log_tool_call(sid2, "read", "h", duration_ms=5.0)
        db.log_tool_call(sid2, "glob", "h", duration_ms=15.0)

        ranking = db.get_tool_usage_ranking(limit=10)
        assert len(ranking) == 3
        # read=4, write=2, glob=1
        assert ranking[0][0] == "read"
        assert ranking[0][1] == 4
        assert ranking[1][0] == "write"
        assert ranking[1][1] == 2
        assert ranking[2][0] == "glob"
        assert ranking[2][1] == 1

    def test_ranking_per_session(self, db: DatabaseManager):
        sid = db.create_session()
        db.log_tool_call(sid, "read", "h", duration_ms=5.0)
        db.log_tool_call(sid, "read", "h", duration_ms=10.0)
        db.log_tool_call(sid, "glob", "h", duration_ms=15.0)

        ranking = db.get_tool_usage_ranking(session_id=sid)
        assert len(ranking) == 2
        assert ranking[0][0] == "read"
        assert ranking[0][1] == 2
        assert ranking[1][0] == "glob"
        assert ranking[1][1] == 1

    def test_ranking_avg_duration(self, db: DatabaseManager):
        sid = db.create_session()
        db.log_tool_call(sid, "read", "h", duration_ms=10.0)
        db.log_tool_call(sid, "read", "h", duration_ms=30.0)

        ranking = db.get_tool_usage_ranking(session_id=sid)
        assert len(ranking) == 1
        assert ranking[0][0] == "read"
        assert ranking[0][1] == 2
        assert ranking[0][2] == pytest.approx(20.0)

    def test_ranking_limit(self, db: DatabaseManager):
        sid = db.create_session()
        for tool in ["a", "b", "c", "d", "e"]:
            db.log_tool_call(sid, tool, "h")
        ranking = db.get_tool_usage_ranking(session_id=sid, limit=3)
        assert len(ranking) == 3
