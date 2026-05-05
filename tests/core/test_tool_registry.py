import os
import warnings

import pytest

from src.core.tool_registry import ToolRegistry

MAX_DOC_LENGTH = int(os.getenv("TOOL_MAX_DOC_LENGTH", "360"))
MAX_FUNC_NAME_LENGTH = int(os.getenv("TOOL_MAX_FUNC_NAME_LENGTH", "80"))
MAX_RESULT_LENGTH = int(os.getenv("TOOL_MAX_RESULT_LENGTH", "30000"))
LIST_TRUNCATE_THRESHOLD = int(os.getenv("TOOL_LIST_TRUNCATE_THRESHOLD", "100"))
DICT_TRUNCATE_THRESHOLD = int(os.getenv("TOOL_DICT_TRUNCATE_THRESHOLD", "100"))


# noinspection PyProtectedMember
@pytest.fixture(autouse=True)
def isolate_tool_registry():
    """自动在每个测试前后隔离 ToolRegistry 单例"""
    from src.core.database_manager import DatabaseManager

    # 保存原始实例
    original_instance = ToolRegistry._instance

    # 重置为 None,让每个测试获得新实例
    ToolRegistry._instance = None

    yield

    # 测试后恢复
    ToolRegistry._instance = original_instance

    # 清理数据库连接,避免 ResourceWarning
    DatabaseManager.reset_instances()


def test_tool_registry_singleton():
    """测试单例模式"""
    registry1 = ToolRegistry()
    registry2 = ToolRegistry()

    assert registry1 is registry2
    assert id(registry1) == id(registry2)


def test_validate_tool_info():
    """测试工具信息验证"""
    registry = ToolRegistry()

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")

        registry._validate_tool_info("short_name", "短文档")

        long_name = "x" * 82
        registry._validate_tool_info(long_name, "正常文档")

        long_doc = "x" * 365
        registry._validate_tool_info("normal_name", long_doc)

    assert len(w) == 2
    assert any(f"超过 {MAX_FUNC_NAME_LENGTH} 字符" in str(warning.message) for warning in w)
    assert any(f"超过 {MAX_DOC_LENGTH} 字符" in str(warning.message) for warning in w)


class TestToolCategorization:
    """测试工具分类逻辑(需要 workspace 注册工具)."""

    @pytest.fixture(autouse=True)
    def setup(self, tmp_path):
        from src.core.database_manager import DatabaseManager
        from src.workspace.workspace import Workspace

        Workspace._instance = None
        DatabaseManager.reset_instances()
        ws = Workspace(str(tmp_path))
        registry = ToolRegistry()
        registry.register(ws)

    def test_query_tools_category(self):
        registry = ToolRegistry()
        for name in ("glob", "ls", "regex_search", "stat", "read", "symbol_ref"):
            assert registry._tool_categories.get(name) == "query", f"{name} should be query"

    def test_write_tools_category(self):
        registry = ToolRegistry()
        for name in ("write", "edit"):
            assert registry._tool_categories.get(name) == "write", f"{name} should be write"

    def test_git_tool_category(self):
        registry = ToolRegistry()
        assert registry._tool_categories.get("git") == "dangerous"

    def test_all_tools_have_category(self):
        registry = ToolRegistry()
        for name in registry._tools:
            assert name in registry._tool_categories, f"{name} missing category"

    def test_git_dangerous_commands_get_pending_audit(self, tmp_path):
        from src.core.database_manager import DatabaseManager
        from src.workspace.workspace import Workspace

        Workspace._instance = None
        DatabaseManager.reset_instances()
        ws = Workspace(str(tmp_path))
        registry = ToolRegistry()
        registry.register(ws)
        session_id = ws.db.create_session()
        registry.set_session_id(session_id)

        # Simulate a dangerous git call
        registry._log_tool_call("git", {"command_str": "add file.txt"}, 10.0, "success")

        rows = ws.db.fetchall("SELECT func_name, audit_status FROM tool_calls")
        assert len(rows) == 1
        assert rows[0][1] == "PENDING_AUDIT"

    def test_git_safe_commands_no_audit(self, tmp_path):
        from src.core.database_manager import DatabaseManager
        from src.workspace.workspace import Workspace

        Workspace._instance = None
        DatabaseManager.reset_instances()
        ws = Workspace(str(tmp_path))
        registry = ToolRegistry()
        registry.register(ws)
        session_id = ws.db.create_session()
        registry.set_session_id(session_id)

        registry._log_tool_call("git", {"command_str": "status"}, 10.0, "success")

        rows = ws.db.fetchall("SELECT func_name, audit_status FROM tool_calls")
        assert len(rows) == 1
        assert rows[0][1] == "none"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
