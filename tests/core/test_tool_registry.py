import asyncio
import os
import warnings
from typing import Any

import pytest

from src.core.tool_registry import ToolInfo, ToolRegistry, extract_params

MAX_DOC_LENGTH = int(os.getenv("TOOL_MAX_DOC_LENGTH", "360"))
MAX_FUNC_NAME_LENGTH = int(os.getenv("TOOL_MAX_FUNC_NAME_LENGTH", "80"))
MAX_RESULT_LENGTH = int(os.getenv("TOOL_MAX_RESULT_LENGTH", "30000"))
LIST_TRUNCATE_THRESHOLD = int(os.getenv("TOOL_LIST_TRUNCATE_THRESHOLD", "100"))
DICT_TRUNCATE_THRESHOLD = int(os.getenv("TOOL_DICT_TRUNCATE_THRESHOLD", "100"))


# noinspection PyProtectedMember
@pytest.fixture(autouse=True)
def isolate_tool_registry():
    """自动在每个测试前后隔离 ToolRegistry 单例"""
    # 保存原始实例
    original_instance = ToolRegistry._instance

    # 重置为 None，让每个测试获得新实例
    ToolRegistry._instance = None

    yield

    # 测试后恢复
    ToolRegistry._instance = original_instance

def test_in_wrapper():
    registry = ToolRegistry()

    @registry.register(name="add")
    def add(a: int, b: int) -> int:
        return a + b

    assert add(3, 2) == 5


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


def test_register_decorator():
    """测试装饰器注册同步工具"""
    registry = ToolRegistry()

    @registry.register(name="add", doc="计算两个数的和")
    def add(a: int, b: int) -> int:
        """这是原有的文档"""
        return a + b

    @registry.register(doc="生成问候语")
    def greet(name: str, greeting: str = "Hello") -> str:
        return f"{greeting}, {name}!"

    assert "add" in registry._tools
    assert "greet" in registry._tools
    assert len(registry.list_tools()["sync"]) == 2

    tool_info = registry.get_tool_info("add")
    assert tool_info is not None
    assert tool_info.name == "add"
    assert tool_info.doc == "计算两个数的和"
    assert "a" in tool_info.params
    assert "b" in tool_info.params


def test_register_decorator_no_args():
    """测试无参数装饰器"""
    registry = ToolRegistry()

    @registry.register()
    def multiply(x: int, y: int) -> int:
        """乘法运算"""
        return x * y

    assert "multiply" in registry._tools
    tool_info = registry.get_tool_info("multiply")
    assert tool_info.doc == "乘法运算"


def test_register_function():
    """测试直接注册函数"""
    registry = ToolRegistry()

    def square(x: int) -> int:
        """计算平方"""
        return x * x

    def cube(x: int) -> int:
        return x**3

    registry.register_function(square, doc="计算平方")
    registry.register_function(cube, name="cube_func", doc="计算立方")

    assert "square" in registry._tools
    assert "cube_func" in registry._tools


def test_execute_sync():
    """测试执行同步工具"""
    registry = ToolRegistry()

    @registry.register(name="concat", doc="连接字符串")
    def concat_strings(a: str, b: str, separator: str = " ") -> str:
        return f"{a}{separator}{b}"

    result = registry.execute("concat", "hello", "world")
    assert result == "hello world"

    result = registry.execute("concat", "hello", "world", separator="-")
    assert result == "hello-world"


def test_execute_nonexistent_tool():
    """测试执行不存在的工具"""
    registry = ToolRegistry()

    with pytest.raises(ValueError, match="未找到工具: nonexistent"):
        registry.execute("nonexistent")


def test_extract_params():
    """测试参数提取功能"""

    def func_with_defaults(a: int, b: str = "default", c: bool = False) -> str:
        """带默认值的函数"""
        return f"{a}_{b}_{c}"

    params = extract_params(func_with_defaults)

    assert "a" in params
    assert "b" in params
    assert "c" in params

    assert params["a"]["required"] is True
    assert params["b"]["required"] is False
    assert params["c"]["required"] is False

    assert params["b"]["default"] == "'default'"
    assert params["c"]["default"] == "False"


def test_extract_params_no_self_cls():
    """测试参数提取忽略self和cls"""

    # noinspection PyUnusedLocal
    def instance_method(self, a: int) -> int:
        return a * 2

    # noinspection PyUnusedLocal
    def class_method(cls, b: str) -> str:
        return b.upper()

    params1 = extract_params(instance_method)
    params2 = extract_params(class_method)

    assert "self" not in params1
    assert "cls" not in params2
    assert "a" in params1
    assert "b" in params2


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


def test_warning_on_empty_doc():
    """测试空文档警告"""
    registry = ToolRegistry()

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")

        @registry.register()
        def no_doc_function(x: int) -> int:
            return x * 2

        assert len(w) == 1
        assert "缺少文档化描述" in str(w[0].message)


def test_compress_result_string():
    """测试字符串结果压缩"""
    registry = ToolRegistry()

    long_string = "x" * (MAX_RESULT_LENGTH + 10000)

    compressed = registry._compress_result(long_string)
    assert len(compressed) == registry.MAX_RESULT_LENGTH + len("... [结果已截断]")
    assert compressed.endswith("... [结果已截断]")


def test_compress_result_list():
    """测试列表结果压缩"""
    registry = ToolRegistry()

    long_list = list(range(150))

    compressed = registry._compress_result(long_list)
    assert len(compressed) == 101
    assert compressed[-1] == "... [列表已截断]"


def test_compress_result_dict():
    """测试字典结果压缩"""
    registry = ToolRegistry()

    long_dict = {f"key_{i}": f"value_{i}" for i in range(150)}

    compressed = registry._compress_result(long_dict)
    assert len(compressed) == 101
    assert compressed["..."] == "[字典已截断]"


def test_no_compress_short_results():
    """测试不对短结果进行压缩"""
    registry = ToolRegistry()

    short_string = "short"
    short_list = [1, 2, 3]
    short_dict = {"a": 1, "b": 2}

    assert registry._compress_result(short_string) == short_string
    assert registry._compress_result(short_list) == short_list
    assert registry._compress_result(short_dict) == short_dict


def test_generate_markdown():
    """测试生成Markdown文档"""
    registry = ToolRegistry()

    @registry.register(name="tool1", doc="第一个工具")
    def tool1(a: int) -> int:
        return a

    @registry.register(name="tool2", doc="第二个工具")
    def tool2(b: str) -> str:
        return b

    @registry.register(name="async1", doc="异步工具")
    async def async1(x: float) -> float:
        return x * 2

    markdown = registry.generate_markdown()

    assert "## 工具" in markdown

    # 检查工具标记
    assert any('<func_name="tool1"' in line for line in markdown.splitlines())
    assert any('<func_name="tool2"' in line for line in markdown.splitlines())
    assert any('<func_name="async1"' in line for line in markdown.splitlines())


def test_get_tool_info():
    """测试获取工具信息"""
    registry = ToolRegistry()

    @registry.register(name="get_data", doc="获取数据")
    def get_data(uid: int, name: str = "default") -> dict:
        return {"id": uid, "name": name}

    tool_info = registry.get_tool_info("get_data")

    assert isinstance(tool_info, ToolInfo)
    assert tool_info.name == "get_data"
    assert tool_info.doc == "获取数据"
    assert "uid" in tool_info.params
    assert "name" in tool_info.params

    # 测试获取不存在的工具
    assert registry.get_tool_info("nonexistent") is None


def test_repr():
    """测试__repr__方法"""
    registry = ToolRegistry()

    @registry.register(name="a")
    def a():
        pass

    repr_str = repr(registry)
    assert "ToolRegistry" in repr_str
    assert "sync_tools=" in repr_str


def test_to_markdown():
    """测试ToolInfo的to_markdown方法"""

    def sample_func(x: int) -> int:
        """示例函数"""
        return x * 2

    tool_info = ToolInfo(
        name="sample", func=sample_func, params={"x": {"required": True, "annotation": "int"}}, doc="示例工具"
    )

    markdown = tool_info.to_markdown()
    assert 'func_name="sample"' in markdown
    assert "示例工具" in markdown


def test_execute_with_large_result():
    """测试执行返回大结果的工具"""
    registry = ToolRegistry()

    @registry.register(name="large_string", doc="返回大字符串")
    def large_string() -> str:
        return "x" * (MAX_RESULT_LENGTH + 10000)

    @registry.register(name="large_list", doc="返回大列表")
    def large_list() -> list[int]:
        return list(range(LIST_TRUNCATE_THRESHOLD + 50))

    @registry.register(name="large_dict", doc="返回大字典")
    def large_dict() -> dict[str, str]:
        return {f"key_{i}": f"value_{i}" for i in range(DICT_TRUNCATE_THRESHOLD + 50)}

    # 测试压缩后的结果
    compressed_str = registry.execute("large_string")
    assert len(compressed_str) == registry.MAX_RESULT_LENGTH + len("... [结果已截断]")
    assert "... [结果已截断]" in compressed_str

    compressed_list = registry.execute("large_list")
    assert len(compressed_list) == 101
    assert "... [列表已截断]" in compressed_list

    compressed_dict = registry.execute("large_dict")
    assert len(compressed_dict) == 101
    assert compressed_dict["..."] == "[字典已截断]"


def test_execute_with_small_result():
    """测试执行返回小结果的工具"""
    registry = ToolRegistry()

    @registry.register(name="small_string", doc="返回小字符串")
    def small_string() -> str:
        return "hello"

    @registry.register(name="small_list", doc="返回小列表")
    def small_list() -> list[int]:
        return [1, 2, 3]

    @registry.register(name="small_dict", doc="返回小字典")
    def small_dict() -> dict[str, int]:
        return {"a": 1, "b": 2}

    # 测试未压缩的结果
    result_str = registry.execute("small_string")
    assert result_str == "hello"

    result_list = registry.execute("small_list")
    assert result_list == [1, 2, 3]

    result_dict = registry.execute("small_dict")
    assert result_dict == {"a": 1, "b": 2}


def test_register_duplicate_name():
    """测试重复注册同名工具"""
    registry = ToolRegistry()

    @registry.register(name="duplicate", doc="第一个函数")
    def func1() -> str:
        return "first"

    @registry.register(name="duplicate", doc="第二个函数")
    def func2() -> str:
        return "second"

    # 第二个函数应该覆盖第一个函数
    result = registry.execute("duplicate")
    assert result == "second"

    tool_info = registry.get_tool_info("duplicate")
    assert tool_info is not None
    assert tool_info.doc == "第二个函数"


def test_register_with_type_hints():
    """测试带类型提示的函数注册"""
    registry = ToolRegistry()

    @registry.register(name="typed_func", doc="带类型提示的函数")
    def typed_func(
        a: int, b: str = "default", c: list[int] | None = None, d: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """带有复杂类型提示的函数"""
        return {"a": a, "b": b, "c": c, "d": d}

    tool_info = registry.get_tool_info("typed_func")
    assert tool_info is not None

    params = tool_info.params
    # 检查类型标注 - Python 3.12+ 中 annotation 返回的是类对象
    assert "int" in str(params["a"]["annotation"])
    assert "str" in str(params["b"]["annotation"])
    assert "list" in str(params["c"]["annotation"]).lower()
    assert params["b"]["default"] == "'default'"
    assert params["c"]["default"] == "None"


@pytest.mark.asyncio
async def test_register_async_function_as_sync():
    """测试注册到同步模式的异步函数"""
    # 创建一个新的注册表名称来避免之前的测试影响
    registry = ToolRegistry()

    # 使用装饰器注册同步函数
    @registry.register(name="decorated_sync", doc="装饰器同步")
    def decorated_sync(x: int) -> int:
        return x * 2

    # 使用装饰器注册异步函数
    @registry.register(name="decorated_async", doc="装饰器异步")
    async def decorated_async(x: int) -> int:
        await asyncio.sleep(0.001)
        return x * 3

    # 直接注册同步函数
    def direct_sync(x: int) -> int:
        """直接注册同步"""
        return x * 4

    registry.register_function(direct_sync, name="direct_sync", doc="直接注册同步")

    # 直接注册异步函数
    async def direct_async(x: int) -> int:
        """直接注册异步"""
        await asyncio.sleep(0.001)
        return x * 5

    registry.register_function(direct_async, name="direct_async", doc="直接注册异步")

    # 测试所有注册方式都工作
    assert registry.execute("decorated_sync", 5) == 10
    assert registry.execute("decorated_async", 5) == 15
    assert registry.execute("direct_sync", 5) == 20
    assert registry.execute("direct_async", 5) == 25


def test_with_raise_register():
    registry = ToolRegistry()

    @registry.register()
    def func() -> int:
        raise ValueError("Test Error")

    assert "ValueError" in registry.execute("func")


def test_long_name_tool():
    registry = ToolRegistry()

    with pytest.warns(UserWarning):

        @registry.register()
        def funnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnc():
            pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
