import hashlib
import os
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
    return ws


@pytest.fixture
def write_tool(workspace: Workspace):
    from src.workspace.tools.write_tool import WriteTool

    return WriteTool(workspace)


@pytest.fixture
def read_tool(workspace: Workspace):
    from src.workspace.tools.read_tool import ReadTool

    return ReadTool(workspace)


class TestWriteNewFile:
    def test_write_new_file_no_mtime_check(self, write_tool, tmp_path: Path):
        result = write_tool.write("new_file.txt", "hello")
        assert "success" in result.lower()

    def test_write_new_file_creates_snapshot(self, write_tool, tmp_path: Path):
        write_tool.write("new_file.txt", "hello")

        rows = write_tool.workspace.db.fetchall("SELECT old_hash, new_hash, audit_status FROM file_snapshots")
        assert len(rows) == 1
        assert rows[0][0] is None
        assert rows[0][2] == "PENDING_AUDIT"


class TestWriteAfterRead:
    def test_write_after_read_succeeds(self, write_tool, read_tool, tmp_path: Path):
        file = tmp_path / "test.txt"
        file.write_text("original", encoding="utf-8")

        read_tool.read("test.txt")
        result = write_tool.write("test.txt", "updated")
        assert "success" in result.lower()

    def test_write_after_read_has_old_hash(self, write_tool, read_tool, tmp_path: Path):
        file = tmp_path / "test.txt"
        file.write_text("original", encoding="utf-8")

        read_tool.read("test.txt")
        write_tool.write("test.txt", "updated")

        rows = write_tool.workspace.db.fetchall("SELECT old_hash, new_hash FROM file_snapshots")
        assert len(rows) == 1
        assert rows[0][0] is not None
        assert rows[0][1] != rows[0][0]


class TestWriteModifiedExternally:
    def test_write_modified_externally_fails(self, write_tool, read_tool, tmp_path: Path):
        file = tmp_path / "test.txt"
        file.write_text("original", encoding="utf-8")

        read_tool.read("test.txt")

        file.write_text("modified externally", encoding="utf-8")
        time.sleep(0.01)

        result = write_tool.write("test.txt", "should fail")
        assert "FILE_MODIFIED_EXTERNALLY" in result

    def test_write_no_prior_read_succeeds(self, write_tool, tmp_path: Path):
        file = tmp_path / "test.txt"
        file.write_text("existing content", encoding="utf-8")

        result = write_tool.write("test.txt", "new content")
        assert "success" in result.lower()


class TestWriteDiffContent:
    def test_write_diff_content(self, write_tool, tmp_path: Path):
        file = tmp_path / "test.txt"
        file.write_text("line1\nline2\nline3", encoding="utf-8")

        from src.workspace.tools.read_tool import ReadTool

        ReadTool(write_tool.workspace).read("test.txt")
        write_tool.write("test.txt", "line1\nmodified\nline3")

        rows = write_tool.workspace.db.fetchall("SELECT diff_content FROM file_snapshots")
        assert len(rows) == 1
        assert "-line2" in rows[0][0]
        assert "+modified" in rows[0][0]

    def test_write_new_file_no_diff(self, write_tool, tmp_path: Path):
        write_tool.write("new_file.txt", "brand new")

        rows = write_tool.workspace.db.fetchall("SELECT diff_content FROM file_snapshots")
        assert len(rows) == 1
        assert "+brand new" in rows[0][0]


class TestWriteUpdatesReadRecord:
    def test_write_updates_read_record(self, write_tool, read_tool, tmp_path: Path):
        file = tmp_path / "test.txt"
        file.write_text("original", encoding="utf-8")

        read_tool.read("test.txt")
        record_before = write_tool.workspace.db.get_file_read_record("test.txt")

        write_tool.write("test.txt", "updated content")
        record_after = write_tool.workspace.db.get_file_read_record("test.txt")

        assert record_after is not None
        assert record_after[4] != record_before[4]
