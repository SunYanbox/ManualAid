from src.workspace.tools.base_tool import BaseTool


def test_extract_params():
    """测试参数提取功能"""

    def func_with_defaults(a: int, b: str = "default", c: bool = False) -> str:
        """带默认值的函数"""
        return f"{a}_{b}_{c}"

    params = BaseTool.extract_params(func_with_defaults)

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

    params1 = BaseTool.extract_params(instance_method)
    params2 = BaseTool.extract_params(class_method)

    assert "self" not in params1
    assert "cls" not in params2
    assert "a" in params1
    assert "b" in params2
