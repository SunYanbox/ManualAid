from src.models.tools.tool_result import ToolResult


def test_compress_result_list():
    """测试列表结果压缩"""
    long_list = list(range(150))

    compressed = ToolResult._compress_result(long_list)
    assert len(compressed) == 101
    assert "列表已截断" in compressed[-1]


def test_compress_result_dict():
    """测试字典结果压缩"""
    long_dict = {f"key_{i}": f"value_{i}" for i in range(150)}

    compressed = ToolResult._compress_result(long_dict)
    assert len(compressed) == 101
    assert "字典已截断" in compressed["..."]


def test_no_compress_short_results():
    """测试不对短结果进行压缩"""
    short_string = "short"
    short_list = [1, 2, 3]
    short_dict = {"a": 1, "b": 2}

    assert ToolResult._compress_result(short_string) == short_string
    assert ToolResult._compress_result(short_list) == short_list
    assert ToolResult._compress_result(short_dict) == short_dict


def test_compress_result_string():
    """测试字符串结果压缩"""
    long_string = "x" * (ToolResult.MAX_RESULT_LENGTH + 10000)

    compressed = ToolResult._compress_result(long_string)
    assert "结果已截断" in compressed
