from src.workspace.tools.base_tool import BaseTool, build_param_doc
from src.workspace.workspace import Workspace


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


def test_build_param_doc():
    """测试参数文档生成使用简洁类型和required属性"""

    params_required = {"required": True, "annotation": "<class 'str'>"}
    result = build_param_doc("file_path", params_required)
    assert 'type="string"' in result
    assert 'required="true"' in result
    assert "<class" not in result

    params_optional = {"required": False, "annotation": "<class 'int'>", "default": "0"}
    result = build_param_doc("max_lines", params_optional)
    assert 'type="integer"' in result
    assert 'required="false"' in result
    assert 'default="0"' in result
    assert "<class" not in result

    params_no_annotation = {"required": True}
    result = build_param_doc("unknown", params_no_annotation)
    assert 'type="string"' in result
    assert 'required="true"' in result


def test_to_doc_new_format():
    """测试 to_doc() 输出新的XML结构"""

    def sample_func(a: str, b: int = 0) -> str:
        """Sample function for testing"""
        return f"{a}_{b}"

    class MockTool(BaseTool):
        def __init__(self, workspace: Workspace | None):
            super().__init__(workspace, "mock", "测试工具")
            self.func = sample_func
            self.params = BaseTool.extract_params(sample_func)

    tool = MockTool(None)
    doc = tool.to_doc()

    # 使用新格式标签
    assert doc.startswith('<func_name="mock">')
    assert "<description>测试工具</description>" in doc
    assert "<params>" in doc
    assert "</params>" in doc
    assert doc.endswith("</func_name>")

    # 验证参数格式
    assert 'type="string"' in doc
    assert 'type="integer"' in doc
    assert 'required="true"' in doc
    assert 'required="false"' in doc

    # 验证没有旧格式标记
    assert "<func_name=" in doc
    assert "<doc>" not in doc
    assert "<required>" not in doc
    assert "<class '" not in doc
