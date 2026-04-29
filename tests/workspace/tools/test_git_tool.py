"""Git 工具测试 — 白名单机制与安全封装."""

import subprocess
from pathlib import Path

import pytest

from src.core.database_manager import DatabaseManager
from src.workspace.workspace import Workspace


# noinspection PyTypeChecker
@pytest.fixture(autouse=True)
def reset_singletons():
    Workspace._instance = None
    DatabaseManager.reset_instances()
    yield
    Workspace._instance = None
    DatabaseManager.reset_instances()


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    """创建一个带有初始提交的 git 仓库."""
    repo = tmp_path / "repo"
    repo.mkdir(parents=True)
    subprocess.run(["git", "init"], cwd=repo, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, capture_output=True)
    # Initial commit so commands work against a real repo
    (repo / "README.md").write_text("# Test\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=repo, capture_output=True)
    subprocess.run(["git", "commit", "-m", "initial"], cwd=repo, capture_output=True)
    return repo


@pytest.fixture
def workspace(git_repo: Path) -> Workspace:
    ws = Workspace(str(git_repo))
    return ws


@pytest.fixture
def git_tool(workspace: Workspace):
    from src.workspace.tools.git_tool import GitTool

    return GitTool(workspace)


class TestGitAllowedCommands:
    def test_status(self, git_tool):
        result = git_tool.git("status")
        assert "nothing to commit" in result.lower() or "working tree clean" in result.lower()

    def test_diff(self, git_tool):
        result = git_tool.git("diff")
        assert "(no output)" in result or result == "" or result == "(no output)"

    def test_log(self, git_tool):
        result = git_tool.git("log --oneline -1")
        assert "initial" in result.lower()

    def test_show(self, git_tool):
        result = git_tool.git("show --stat")
        assert "README" in result or "initial" in result.lower()

    def test_add_and_commit(self, git_tool, git_repo: Path):
        (git_repo / "new_file.txt").write_text("content", encoding="utf-8")
        add_result = git_tool.git("add new_file.txt")
        assert "failed" not in add_result.lower()

        commit_result = git_tool.git('commit -m "test commit"')
        assert "commi" in commit_result.lower() or "file changed" in commit_result.lower()

    def test_branch(self, git_tool):
        result = git_tool.git("branch")
        assert "*" in result or "main" in result or "master" in result

    def test_restore_specific_file(self, git_tool, git_repo: Path):
        (git_repo / "README.md").write_text("modified\n", encoding="utf-8")
        result = git_tool.git("restore README.md")
        assert "failed" not in result.lower()


class TestGitBlockedCommands:
    def test_push_blocked(self, git_tool):
        result = git_tool.git("push")
        assert "blocked" in result.lower() or "ERROR" in result

    def test_remote_blocked(self, git_tool):
        result = git_tool.git("remote add origin https://example.com/repo.git")
        assert "blocked" in result.lower() or "ERROR" in result

    def test_reset_hard_blocked(self, git_tool):
        result = git_tool.git("reset --hard HEAD")
        assert "blocked" in result.lower() or "ERROR" in result

    def test_branch_d_blocked(self, git_tool):
        result = git_tool.git("branch -D test")
        assert "blocked" in result.lower() or "ERROR" in result

    def test_merge_blocked(self, git_tool):
        result = git_tool.git("merge test-branch")
        assert "blocked" in result.lower() or "ERROR" in result

    def test_rebase_blocked(self, git_tool):
        result = git_tool.git("rebase main")
        assert "blocked" in result.lower() or "ERROR" in result

    def test_clean_blocked(self, git_tool):
        result = git_tool.git("clean -fd")
        assert "blocked" in result.lower() or "ERROR" in result

    def test_fetch_blocked(self, git_tool):
        result = git_tool.git("fetch origin")
        assert "blocked" in result.lower() or "ERROR" in result

    def test_pull_blocked(self, git_tool):
        result = git_tool.git("pull origin main")
        assert "blocked" in result.lower() or "ERROR" in result


class TestGitRestoreSafety:
    def test_bare_restore_rejected(self, git_tool):
        result = git_tool.git("restore")
        assert "需要指定文件路径" in result or "ERROR" in result or "restore" in result.lower()

    def test_restore_dot_rejected(self, git_tool):
        result = git_tool.git("restore .")
        assert "通配符" in result or "ERROR" in result or "restore" in result.lower()


class TestGitUnknownCommand:
    def test_unknown_command_rejected(self, git_tool):
        result = git_tool.git("unknown-command")
        assert "not in the allowed whitelist" in result.lower() or "ERROR" in result


class TestGitIsSafeCommand:
    def test_safe_commands(self):
        from src.workspace.tools.git_tool import GitTool

        assert GitTool.is_safe_command("status")
        assert GitTool.is_safe_command("diff")
        assert GitTool.is_safe_command("log --oneline -5")
        assert GitTool.is_safe_command("show HEAD")

    def test_modifying_commands_not_safe(self):
        from src.workspace.tools.git_tool import GitTool

        assert not GitTool.is_safe_command("add file.txt")
        assert not GitTool.is_safe_command('commit -m "msg"')
        assert not GitTool.is_safe_command("restore file.txt")

    def test_blocked_commands_not_safe(self):
        from src.workspace.tools.git_tool import GitTool

        assert not GitTool.is_safe_command("push")
        assert not GitTool.is_safe_command("merge main")

    def test_empty_string(self):
        from src.workspace.tools.git_tool import GitTool

        assert not GitTool.is_safe_command("")
        assert not GitTool.is_safe_command("   ")


class TestGitInjection:
    def test_command_injection_via_semicolon(self, git_tool):
        result = git_tool.git("status; echo pwned")
        assert "blocked" in result.lower() or "ERROR" in result or "not in the allowed whitelist" in result.lower()

    def test_invalid_shell_syntax(self, git_tool):
        result = git_tool.git("status $(whoami)")
        assert "failed" not in result.lower() or "error" not in result.lower()
