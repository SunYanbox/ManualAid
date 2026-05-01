import time
from pathlib import Path

import pytest

from src.core.audit_committer import AuditCommitter
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
def committer(workspace: Workspace) -> AuditCommitter:
    return AuditCommitter(workspace)


def _create_pending_snapshot(workspace: Workspace, file_path: str, pending_content: str) -> int:
    """Helper to create a PENDING_AUDIT snapshot."""
    return workspace.db.record_file_snapshot(
        file_path,
        "old_hash",
        "new_hash",
        "diff_content",
        audit_status="PENDING_AUDIT",
        pending_content=pending_content,
    )


class TestCommitNewFile:
    def test_approve_creates_new_file(self, committer: AuditCommitter, workspace: Workspace):
        snapshot_id = _create_pending_snapshot(workspace, "new_file.txt", "hello world")
        result = committer.commit(snapshot_id, approved=True)

        assert "已批准" in result
        target = workspace.root_path / "new_file.txt"
        assert target.is_file()
        assert target.read_text(encoding="utf-8") == "hello world"

    def test_approve_updates_audit_status(self, committer: AuditCommitter, workspace: Workspace):
        snapshot_id = _create_pending_snapshot(workspace, "new_file.txt", "content")
        committer.commit(snapshot_id, approved=True)

        snap = workspace.db.get_snapshot_by_id(snapshot_id)
        assert snap is not None
        assert snap[7] == "APPROVED"

    def test_approve_creates_file_in_subdir(self, committer: AuditCommitter, workspace: Workspace):
        snapshot_id = _create_pending_snapshot(workspace, "sub/dir/new_file.txt", "nested")
        committer.commit(snapshot_id, approved=True)

        target = workspace.root_path / "sub" / "dir" / "new_file.txt"
        assert target.is_file()
        assert target.read_text(encoding="utf-8") == "nested"


class TestCommitExistingFile:
    def test_approve_existing_file_with_read(self, committer: AuditCommitter, workspace: Workspace):
        target = workspace.root_path / "test.txt"
        target.write_text("original", encoding="utf-8")

        workspace.db.record_file_read("test.txt", target.stat().st_mtime, target.stat().st_size, "hash")

        snapshot_id = _create_pending_snapshot(workspace, "test.txt", "updated content")
        result = committer.commit(snapshot_id, approved=True)

        assert "已批准" in result
        assert target.read_text(encoding="utf-8") == "updated content"

    def test_approve_existing_file_no_read_record(self, committer: AuditCommitter, workspace: Workspace):
        target = workspace.root_path / "test.txt"
        target.write_text("original", encoding="utf-8")

        snapshot_id = _create_pending_snapshot(workspace, "test.txt", "updated content")
        result = committer.commit(snapshot_id, approved=True)

        assert "已批准" in result
        assert target.read_text(encoding="utf-8") == "updated content"

    def test_approve_mtime_mismatch_fails(self, committer: AuditCommitter, workspace: Workspace):
        target = workspace.root_path / "test.txt"
        target.write_text("original", encoding="utf-8")

        workspace.db.record_file_read("test.txt", target.stat().st_mtime, target.stat().st_size, "hash")

        # Modify file externally
        time.sleep(0.1)
        target.write_text("modified externally", encoding="utf-8")

        snapshot_id = _create_pending_snapshot(workspace, "test.txt", "should fail")
        result = committer.commit(snapshot_id, approved=True)

        assert "ERROR" in result or "已被外部修改" in result
        assert target.read_text(encoding="utf-8") == "modified externally"


class TestCommitReject:
    def test_reject_does_not_write(self, committer: AuditCommitter, workspace: Workspace):
        snapshot_id = _create_pending_snapshot(workspace, "should_not_exist.txt", "content")
        result = committer.commit(snapshot_id, approved=False)

        assert "已拒绝" in result
        assert not (workspace.root_path / "should_not_exist.txt").is_file()

    def test_reject_updates_status(self, committer: AuditCommitter, workspace: Workspace):
        snapshot_id = _create_pending_snapshot(workspace, "test.txt", "content")
        committer.commit(snapshot_id, approved=False)

        snap = workspace.db.get_snapshot_by_id(snapshot_id)
        assert snap is not None
        assert snap[7] == "REJECTED"


class TestCommitEdgeCases:
    def test_commit_nonexistent_snapshot(self, committer: AuditCommitter):
        result = committer.commit(9999, approved=True)
        assert "不存在" in result

    def test_commit_already_approved(self, committer: AuditCommitter, workspace: Workspace):
        snapshot_id = _create_pending_snapshot(workspace, "test.txt", "content")
        committer.commit(snapshot_id, approved=True)

        result = committer.commit(snapshot_id, approved=True)
        assert "已处理" in result

    def test_commit_already_rejected(self, committer: AuditCommitter, workspace: Workspace):
        snapshot_id = _create_pending_snapshot(workspace, "test.txt", "content")
        committer.commit(snapshot_id, approved=False)

        result = committer.commit(snapshot_id, approved=False)
        assert "已处理" in result


class TestCommitBinaryProtection:
    """测试审计提交器的二进制文件安全网."""

    def test_commit_binary_ext_blocked(self, committer: AuditCommitter, workspace: Workspace):
        """批准写入 .png 文件应被安全网拦截."""
        snapshot_id = _create_pending_snapshot(workspace, "image.png", "fake png")
        result = committer.commit(snapshot_id, approved=True)

        assert "二进制文件" in result
        assert not (workspace.root_path / "image.png").is_file()
        # 状态应被标记为 REJECTED
        snap = workspace.db.get_snapshot_by_id(snapshot_id)
        assert snap[7] == "REJECTED"

    def test_commit_binary_content_blocked(self, committer: AuditCommitter, workspace: Workspace):
        """批准写入内容为二进制的文件应被安全网拦截."""
        # 先在磁盘上创建一个二进制文件
        target = workspace.root_path / "data.unknown"
        target.write_bytes(b"\x00\xff\xfe")

        snapshot_id = _create_pending_snapshot(workspace, "data.unknown", "overwrite")
        result = committer.commit(snapshot_id, approved=True)

        assert "二进制文件" in result
        # 文件内容不应被改变
        assert target.read_bytes() == b"\x00\xff\xfe"

    def test_commit_text_file_not_blocked(self, committer: AuditCommitter, workspace: Workspace):
        """批准写入文本文件应正常通过."""
        snapshot_id = _create_pending_snapshot(workspace, "notes.txt", "hello")
        result = committer.commit(snapshot_id, approved=True)

        assert "已批准" in result
        assert (workspace.root_path / "notes.txt").read_text(encoding="utf-8") == "hello"
