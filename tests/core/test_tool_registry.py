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


def test_validate_config():
    """测试配置验证 - 一次性测试所有阈值"""
    config = ToolRegistry()

    # 设置所有值为过小
    config.MAX_RESULT_LENGTH = 5
    config.LIST_TRUNCATE_THRESHOLD = 3
    config.DICT_TRUNCATE_THRESHOLD = 2

    # 验证触发3个警告
    with pytest.warns(UserWarning) as record:
        config._validate_config()

    # 验证警告数量和内容
    assert len(record) == 3
    assert "TOOL_MAX_RESULT_LENGTH" in str(record[0].message)
    assert "TOOL_LIST_TRUNCATE_THRESHOLD" in str(record[1].message)
    assert "TOOL_DICT_TRUNCATE_THRESHOLD" in str(record[2].message)

    # 验证所有值都被修正
    assert config.MAX_RESULT_LENGTH == 100
    assert config.LIST_TRUNCATE_THRESHOLD == 50
    assert config.DICT_TRUNCATE_THRESHOLD == 50


def test_tool_registry_singleton():
    """测试单例模式"""
    registry1 = ToolRegistry()
    registry2 = ToolRegistry()

    assert registry1 is registry2
    assert id(registry1) == id(registry2)


def test_execute_nonexistent_tool():
    """测试执行不存在的工具"""
    registry = ToolRegistry()

    with pytest.raises(ValueError, match="未找到工具: nonexistent"):
        registry.execute("nonexistent")


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


def test_compress_result_string():
    """测试字符串结果压缩"""
    registry = ToolRegistry()

    long_string = "x" * (MAX_RESULT_LENGTH + 10000)

    compressed = registry._compress_result(long_string)
    assert "结果已截断" in compressed


def test_compress_result_list():
    """测试列表结果压缩"""
    registry = ToolRegistry()

    long_list = list(range(150))

    compressed = registry._compress_result(long_list)
    assert len(compressed) == 101
    assert "列表已截断" in compressed[-1]


def test_compress_result_dict():
    """测试字典结果压缩"""
    registry = ToolRegistry()

    long_dict = {f"key_{i}": f"value_{i}" for i in range(150)}

    compressed = registry._compress_result(long_dict)
    assert len(compressed) == 101
    assert "字典已截断" in compressed["..."]


def test_no_compress_short_results():
    """测试不对短结果进行压缩"""
    registry = ToolRegistry()

    short_string = "short"
    short_list = [1, 2, 3]
    short_dict = {"a": 1, "b": 2}

    assert registry._compress_result(short_string) == short_string
    assert registry._compress_result(short_list) == short_list
    assert registry._compress_result(short_dict) == short_dict


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
        for name in ("glob", "ls", "regex_search", "stat", "read", "read_lines", "symbol_ref"):
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
