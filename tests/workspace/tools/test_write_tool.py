import time
from pathlib import Path

import pytest

from src.core.database_manager import DatabaseManager
from src.workspace.workspace import Workspace


@pytest.fixture(autouse=True)
def reset_singletons():
    Workspace._instance = None
    DatabaseManager.reset_instances()
    yield
    Workspace._instance = None
    DatabaseManager.reset_instances()


@pytest.fixture
def workspace(tmp_path: Path) -> Workspace:
    ws = Workspace(str(tmp_path))
    ws._current_session_id = ws.db.create_session(name="test_session")
    return ws


@pytest.fixture
def write_tool(workspace: Workspace):
    from src.workspace.tools.write_tool import WriteTool

    return WriteTool(workspace)


@pytest.fixture
def read_tool(workspace: Workspace):
    from src.workspace.tools.read_tool import ReadTool

    return ReadTool(workspace)


class TestWritePreview:
    def test_write_returns_preview(self, write_tool, tmp_path: Path):
        result = write_tool.write("new_file.txt", "hello")
        assert "Write Preview" in result.data
        assert "Snapshot ID:" in result.data

    def test_write_does_not_write_to_disk(self, write_tool, tmp_path: Path):
        write_tool.write("new_file.txt", "hello")
        assert not (tmp_path / "new_file.txt").is_file()

    def test_write_creates_snapshot(self, write_tool, tmp_path: Path):
        write_tool.write("new_file.txt", "hello")

        rows = write_tool.workspace.db.fetchall("SELECT old_hash, new_hash, audit_status, pending_content FROM file_snapshots")
        assert len(rows) == 1
        assert rows[0][0] is None  # old_hash for new file
        assert rows[0][2] == "PENDING_AUDIT"
        assert rows[0][3] == "hello"

    def test_write_preview_contains_diff(self, write_tool, tmp_path: Path):
        write_tool.write("new_file.txt", "line1\nline2\nline3")
        rows = write_tool.workspace.db.fetchall("SELECT diff_content FROM file_snapshots")
        assert len(rows) == 1
        assert "+line1" in rows[0][0]


class TestWriteAfterRead:
    def test_write_after_read_contains_old_hash(self, write_tool, read_tool, tmp_path: Path):
        file = tmp_path / "test.txt"
        file.write_text("original", encoding="utf-8")

        read_tool.read("test.txt")
        write_tool.write("test.txt", "updated")

        rows = write_tool.workspace.db.fetchall("SELECT old_hash, new_hash FROM file_snapshots")
        assert len(rows) == 1
        assert rows[0][0] is not None
        assert rows[0][1] != rows[0][0]

    def test_write_after_read_shows_diff(self, write_tool, read_tool, tmp_path: Path):
        file = tmp_path / "test.txt"
        file.write_text("line1\nline2\nline3", encoding="utf-8")

        read_tool.read("test.txt")
        result = write_tool.write("test.txt", "line1\nmodified\nline3")

        assert "Write Preview" in result.data
        rows = write_tool.workspace.db.fetchall("SELECT diff_content FROM file_snapshots")
        assert len(rows) == 1
        assert "-line2" in rows[0][0]
        assert "+modified" in rows[0][0]


class TestWriteModifiedExternally:
    def test_write_modified_externally_fails(self, write_tool, read_tool, tmp_path: Path):
        file = tmp_path / "test.txt"
        file.write_text("original", encoding="utf-8")

        read_tool.read("test.txt")

        file.write_text("modified externally", encoding="utf-8")
        time.sleep(0.1)

        new_mtime = file.stat().st_mtime
        read_record = read_tool.workspace.db.get_file_read_record(read_tool.workspace._current_session_id, "test.txt")
        stored_mtime = read_record[3] if read_record else None

        if stored_mtime and abs(new_mtime - stored_mtime) < 0.001:
            file.write_text("modified externally again", encoding="utf-8")
            time.sleep(0.1)

        result = write_tool.write("test.txt", "should fail")
        assert result.success is False
        assert "FILE_MODIFIED_EXTERNALLY" in result.error

    def test_write_no_prior_read_succeeds(self, write_tool, tmp_path: Path):
        file = tmp_path / "test.txt"
        file.write_text("existing content", encoding="utf-8")

        result = write_tool.write("test.txt", "new content")
        assert "Write Preview" in result.data


class TestWriteSnapshotPendingContent:
    def test_pending_content_stored(self, write_tool, tmp_path: Path):
        write_tool.write("new_file.txt", "pending content here")

        rows = write_tool.workspace.db.fetchall("SELECT pending_content FROM file_snapshots")
        assert len(rows) == 1
        assert rows[0][0] == "pending content here"

    def test_pending_content_for_existing_file(self, write_tool, read_tool, tmp_path: Path):
        file = tmp_path / "test.txt"
        file.write_text("original", encoding="utf-8")

        read_tool.read("test.txt")
        write_tool.write("test.txt", "updated content")

        snap = write_tool.workspace.db.fetchone("SELECT pending_content, audit_status FROM file_snapshots WHERE file_path = 'test.txt'")
        assert snap is not None
        assert snap[0] == "updated content"
        assert snap[1] == "PENDING_AUDIT"

    def test_disk_file_unchanged_after_write(self, write_tool, read_tool, tmp_path: Path):
        file = tmp_path / "test.txt"
        file.write_text("original", encoding="utf-8")

        read_tool.read("test.txt")
        write_tool.write("test.txt", "should not change disk")

        assert file.read_text(encoding="utf-8") == "original"
