"""Edit 工具测试 — 安全的字符串替换编辑工具."""

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
def edit_tool(workspace: Workspace):
    from src.workspace.tools.edit_tool import EditTool

    return EditTool(workspace)


@pytest.fixture
def read_tool(workspace: Workspace):
    from src.workspace.tools.read_tool import ReadTool

    return ReadTool(workspace)


def _create_file(workspace: Workspace, path: str, content: str) -> Path:
    """Create a file in the workspace."""
    target = workspace.root_path / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return target


class TestEditBasic:
    def test_simple_replacement(self, edit_tool, workspace):
        _create_file(workspace, "test.txt", "hello world")
        result = edit_tool.edit("test.txt", "world", "there")

        assert "Edit Preview" in result.data
        assert "Snapshot ID:" in result.data

    def test_does_not_write_to_disk(self, edit_tool, workspace):
        file = _create_file(workspace, "test.txt", "hello world")
        edit_tool.edit("test.txt", "world", "there")

        assert file.read_text(encoding="utf-8") == "hello world"

    def test_creates_pending_snapshot(self, edit_tool, workspace):
        _create_file(workspace, "test.txt", "hello world")
        edit_tool.edit("test.txt", "world", "there")

        rows = workspace.db.fetchall("SELECT audit_status, pending_content FROM file_snapshots")
        assert len(rows) == 1
        assert rows[0][0] == "PENDING_AUDIT"
        assert rows[0][1] == "hello there"

    def test_diff_in_preview(self, edit_tool, workspace):
        _create_file(workspace, "test.txt", "line1\nline2\nline3")
        result = edit_tool.edit("test.txt", "line2", "modified")

        assert "-line2" in result.data
        assert "+modified" in result.data

    def test_multiple_replacements(self, edit_tool, workspace):
        _create_file(workspace, "test.txt", "a a a a a")
        result = edit_tool.edit("test.txt", "a", "b", max_replacements=3)

        assert "Replacements: 3" in result.data
        # Verify pending content has exactly 3 replacements
        snap = workspace.db.fetchone("SELECT pending_content FROM file_snapshots")
        assert snap is not None
        assert snap[0] == "b b b a a"

    def test_no_match_found(self, edit_tool, workspace):
        _create_file(workspace, "test.txt", "hello world")
        result = edit_tool.edit("test.txt", "nonexistent", "replacement")

        assert "No changes made" in result.data
        assert "old_string not found" in result.data


class TestEditMaxReplacements:
    def test_exceeds_max_replacements(self, edit_tool, workspace):
        _create_file(workspace, "test.txt", "a a a a a a a a a a a a")  # 12 a's
        result = edit_tool.edit("test.txt", "a", "b", max_replacements=5)

        assert "Replacements: 5" in result.data

    def test_max_replacements_default_10(self, edit_tool, workspace):
        _create_file(workspace, "test.txt", " ".join(["a"] * 20))
        result = edit_tool.edit("test.txt", "a", "b")

        assert "Replacements: 10" in result.data

    def test_max_replacements_capped_at_100(self, edit_tool, workspace):
        _create_file(workspace, "test.txt", "a " * 150)
        result = edit_tool.edit("test.txt", "a", "b", max_replacements=200)

        assert "Replacements: 100" in result.data


class TestEditContextValidation:
    def test_context_before_matches(self, edit_tool, workspace):
        _create_file(workspace, "test.txt", "prefix target suffix")
        result = edit_tool.edit("test.txt", "target", "replaced", context_before="prefix ")

        assert "Edit Preview" in result.data

    def test_context_before_mismatch(self, edit_tool, workspace):
        _create_file(workspace, "test.txt", "prefix target suffix")
        result = edit_tool.edit("test.txt", "target", "replaced", context_before="wrong ")

        assert "context_before" in result.data
        assert "mismatch" in result.data.lower()

    def test_context_after_matches(self, edit_tool, workspace):
        _create_file(workspace, "test.txt", "prefix target suffix")
        result = edit_tool.edit("test.txt", "target", "replaced", context_after=" suffix")

        assert "Edit Preview" in result.data

    def test_context_after_mismatch(self, edit_tool, workspace):
        _create_file(workspace, "test.txt", "prefix target suffix")
        result = edit_tool.edit("test.txt", "target", "replaced", context_after=" wrong")

        assert "context_after" in result.data
        assert "mismatch" in result.data.lower()

    def test_both_contexts_match(self, edit_tool, workspace):
        _create_file(workspace, "test.txt", "before target after")
        result = edit_tool.edit("test.txt", "target", "replaced", context_before="before ", context_after=" after")

        assert "Edit Preview" in result.data

    def test_context_with_multiple_matches(self, edit_tool, workspace):
        _create_file(workspace, "test.txt", "before X after\nignore\nbefore X after")
        result = edit_tool.edit(
            "test.txt", "X", "Y", max_replacements=2, context_before="before ", context_after=" after"
        )

        assert "Edit Preview" in result.data
        assert "Replacements: 2" in result.data


class TestEditMtimeValidation:
    def test_edit_modified_externally_fails(self, edit_tool, read_tool, workspace):
        file = _create_file(workspace, "test.txt", "original content")
        read_tool.read("test.txt")

        # Modify externally
        time.sleep(0.1)
        file.write_text("modified externally", encoding="utf-8")

        result = edit_tool.edit("test.txt", "original", "replaced")
        assert "FILE_MODIFIED_EXTERNALLY" in result.data

    def test_edit_no_prior_read_succeeds(self, edit_tool, workspace):
        _create_file(workspace, "test.txt", "original content")
        result = edit_tool.edit("test.txt", "original", "updated")

        assert "Edit Preview" in result.data


class TestEditEdgeCases:
    def test_empty_old_string(self, edit_tool, workspace):
        _create_file(workspace, "test.txt", "content")
        result = edit_tool.edit("test.txt", "", "replacement")

        assert "不能为空" in result.data or "empty" in result.data.lower()

    def test_nonexistent_file(self, edit_tool, workspace):
        result = edit_tool.edit("nonexistent.txt", "old", "new")
        assert "不存在" in result.data or "not found" in result.data.lower() or "exists" in result.data.lower()

    def test_file_outside_workspace(self, edit_tool, workspace):
        result = edit_tool.edit("../outside.txt", "old", "new")
        assert "越界" in result.error or "boundary" in result.error.lower() or "outside" in result.error.lower()

    def test_edit_snapshot_has_old_hash(self, edit_tool, workspace):
        _create_file(workspace, "test.txt", "original")
        edit_tool.edit("test.txt", "original", "updated")

        snap = workspace.db.fetchone("SELECT old_hash, new_hash FROM file_snapshots")
        assert snap is not None
        assert snap[0] is not None
        assert snap[1] is not None
        assert snap[0] != snap[1]
