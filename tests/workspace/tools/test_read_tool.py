import hashlib
from pathlib import Path

import pytest

from src.core.database_manager import DatabaseManager
from src.core.file_tracker import FileTracker
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


class TestReadToolMtimeRecording:
    def test_read_records_mtime(self, workspace: Workspace, tmp_path: Path):
        file = tmp_path / "test.txt"
        file.write_text("hello", encoding="utf-8")

        from src.workspace.tools.read_tool import ReadTool

        tool = ReadTool(workspace)
        result = tool.read("test.txt")

        assert "hello" in result
        record = workspace.db.get_file_read_record("test.txt")
        assert record is not None
        assert record[2] == pytest.approx(file.stat().st_mtime, abs=0.01)

    def test_read_records_checksum(self, workspace: Workspace, tmp_path: Path):
        file = tmp_path / "test.txt"
        content = "checksum test"
        file.write_text(content, encoding="utf-8")

        from src.workspace.tools.read_tool import ReadTool

        tool = ReadTool(workspace)
        tool.read("test.txt")

        record = workspace.db.get_file_read_record("test.txt")
        assert record is not None
        expected_checksum = hashlib.blake2b(content.encode("utf-8")).hexdigest()
        assert record[4] == expected_checksum

    def test_read_nonexistent_file_no_db_record(self, workspace: Workspace):
        from src.workspace.tools.read_tool import ReadTool

        tool = ReadTool(workspace)
        result = tool.read("nonexistent.txt")

        assert "error" in result.lower() or "Error" in result
        record = workspace.db.get_file_read_record("nonexistent.txt")
        assert record is None

    def test_read_updates_read_count(self, workspace: Workspace, tmp_path: Path):
        file = tmp_path / "test.txt"
        file.write_text("content", encoding="utf-8")

        from src.workspace.tools.read_tool import ReadTool

        tool = ReadTool(workspace)
        tool.read("test.txt")
        tool.read("test.txt")

        record = workspace.db.get_file_read_record("test.txt")
        assert record is not None
        assert record[6] == 2


class TestReadLinesToolMtimeRecording:
    def test_read_lines_records_mtime(self, workspace: Workspace, tmp_path: Path):
        file = tmp_path / "test.txt"
        file.write_text("line1\nline2\nline3", encoding="utf-8")

        from src.workspace.tools.read_lines_tool import ReadLinesTool

        tool = ReadLinesTool(workspace)
        result = tool.read_lines("test.txt", 1, 2)

        assert "line1" in result
        record = workspace.db.get_file_read_record("test.txt")
        assert record is not None
