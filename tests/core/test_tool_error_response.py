import pytest

from src.models.tool_error_response import ToolErrorResponse


class TestToolErrorResponse:
    """测试 ToolErrorResponse 数据类"""

    def test_init_with_string_error(self):
        """测试使用字符串错误初始化"""
        response = ToolErrorResponse("test_tool", "connection failed")

        assert response.tool_name == "test_tool"
        assert response.errors == "connection failed"

    def test_init_with_exception_error(self):
        """测试使用异常对象初始化"""
        try:
            raise ValueError("invalid input")
        except ValueError as e:
            response = ToolErrorResponse("test_tool", e)

        assert response.tool_name == "test_tool"
        assert response.errors == "ValueError(invalid input)"

    def test_init_with_custom_exception(self):
        """测试使用自定义异常初始化"""

        class CustomError(Exception):
            pass

        response = ToolErrorResponse("my_tool", CustomError("something wrong"))

        assert response.tool_name == "my_tool"
        assert response.errors == "CustomError(something wrong)"

    def test_to_str_returns_string_representation(self):
        """测试 to_str 方法返回字符串表示"""
        response = ToolErrorResponse("database", "timeout")

        result = response.to_str()

        assert isinstance(result, str)
        assert result == "<tool_name=database, errors=timeout />"

    def test_str_method(self):
        """测试 __str__ 方法"""
        response = ToolErrorResponse("api", "404 not found")

        result = str(response)

        assert result == "<tool_name=api, errors=404 not found />"

    def test_to_str_and_str_are_consistent(self):
        """测试 to_str 和 __str__ 返回相同结果"""
        response = ToolErrorResponse("worker", "failed")

        assert response.to_str() == str(response)

    def test_with_empty_error_string(self):
        """测试空字符串错误"""
        response = ToolErrorResponse("test", "")

        assert response.tool_name == "test"
        assert response.errors == ""
        assert str(response) == "<tool_name=test, errors= />"

    def test_with_special_characters_in_error(self):
        """测试错误消息包含特殊字符"""
        error_msg = 'error with "quotes" and <tags>'
        response = ToolErrorResponse("parser", error_msg)

        assert response.errors == error_msg
        assert error_msg in str(response)

    @pytest.mark.parametrize(
        "tool_name,error_input,expected_error_str",
        [
            ("tool1", "simple error", "simple error"),
            ("tool2", ValueError("bad value"), "ValueError(bad value)"),
            ("tool3", TypeError("wrong type"), "TypeError(wrong type)"),
            ("", "empty tool name", "empty tool name"),
            ("tool with spaces", KeyError("missing key"), "KeyError('missing key')"),  # KeyError会自动添加引号
        ],
    )
    def test_various_error_types(self, tool_name, error_input, expected_error_str):
        """参数化测试:测试多种错误类型"""
        response = ToolErrorResponse(tool_name, error_input)

        assert response.tool_name == tool_name
        assert response.errors == expected_error_str
