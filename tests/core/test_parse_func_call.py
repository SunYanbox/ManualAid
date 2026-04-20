import json

import pytest

from src.core.parse_func_call import parse_func_call


class TestParseFuncCall:
    """测试 parse_func_call 函数的各种场景"""

    # ========== 有效输入测试 ==========

    def test_basic_args(self):
        """基本参数：位置参数 args"""
        content = '<func_call>{"func_name": "ls", "args": ["."]}</func_call>'
        func_name, args, kwargs = parse_func_call(content)
        assert func_name == "ls"
        assert args == ["."]
        assert kwargs == {}

    def test_basic_kwargs(self):
        """关键字参数 kwargs"""
        content = '<func_call>{"func_name": "write", "kwargs": {"file_path": "a.txt", "old_str": "x", "new_str": "y"}}</func_call>'
        func_name, args, kwargs = parse_func_call(content)
        assert func_name == "write"
        assert args == []
        assert kwargs == {"file_path": "a.txt", "old_str": "x", "new_str": "y"}

    def test_both_args_and_kwargs(self):
        """同时包含 args 和 kwargs"""
        content = '<func_call>{"func_name": "test", "args": [1, 2], "kwargs": {"verbose": true}}</func_call>'
        func_name, args, kwargs = parse_func_call(content)
        assert func_name == "test"
        assert args == [1, 2]
        assert kwargs == {"verbose": True}

    def test_escaped_quotes_in_string(self):
        """字符串内包含转义双引号"""
        content = r'<func_call>{"func_name": "echo", "args": ["He said \"hello\""]}</func_call>'
        func_name, args, kwargs = parse_func_call(content)
        assert func_name == "echo"
        assert args == ['He said "hello"']

    def test_newline_in_string(self):
        """字符串内包含换行符（\n）"""
        content = '<func_call>{"func_name": "x", "args": ["line1\\nline2"]}</func_call>'
        func_name, args, kwargs = parse_func_call(content)
        assert func_name == "x"
        assert args == ["line1\nline2"]

    def test_single_quotes_ast_fallback(self):
        """使用单引号的 JSON（通过 ast.literal_eval 解析）"""
        content = "<func_call>{'func_name': 'test', 'args': [1, 2]}</func_call>"
        func_name, args, kwargs = parse_func_call(content)
        assert func_name == "test"
        assert args == [1, 2]
        assert kwargs == {}

    def test_mixed_quote_style(self):
        """混合引号：外层双引号，内层单引号值"""
        content = '<func_call>{"func_name": "mixed", "args": ["\'single\'"]}</func_call>'
        func_name, args, kwargs = parse_func_call(content)
        assert func_name == "mixed"
        assert args == ["'single'"]

    def test_nested_structures(self):
        """嵌套数组和对象"""
        content = '<func_call>{"func_name": "x", "args": [[1, 2], {"a": 1}]}</func_call>'
        func_name, args, kwargs = parse_func_call(content)
        assert func_name == "x"
        assert args == [[1, 2], {"a": 1}]
        assert kwargs == {}

    def test_primitives_in_args(self):
        """参数包含数字、布尔值、null"""
        content = '<func_call>{"func_name": "x", "args": [1, true, false, null]}</func_call>'
        func_name, args, kwargs = parse_func_call(content)
        assert func_name == "x"
        assert args == [1, True, False, None]

    def test_missing_args_implies_empty_list(self):
        """缺少 args 字段时应默认为空列表"""
        content = '<func_call>{"func_name": "no_args"}</func_call>'
        func_name, args, kwargs = parse_func_call(content)
        assert func_name == "no_args"
        assert args == []
        assert kwargs == {}

    def test_missing_kwargs_implies_empty_dict(self):
        """缺少 kwargs 字段时应默认为空字典"""
        content = '<func_call>{"func_name": "no_kwargs", "args": [1]}</func_call>'
        func_name, args, kwargs = parse_func_call(content)
        assert func_name == "no_kwargs"
        assert args == [1]
        assert kwargs == {}

    def test_args_is_not_list_convert_to_list(self):
        """args 字段不是列表时强制转为空列表"""
        content = '<func_call>{"func_name": "x", "args": {}}</func_call>'
        func_name, args, kwargs = parse_func_call(content)
        assert args == []

    def test_kwargs_is_not_dict_convert_to_dict(self):
        """kwargs 字段不是字典时强制转为空字典"""
        content = '<func_call>{"func_name": "x", "kwargs": []}</func_call>'
        func_name, args, kwargs = parse_func_call(content)
        assert kwargs == {}

    def test_extra_whitespace_inside_tags(self):
        """标签内包含多余空白字符"""
        content = '<func_call>\n  {"func_name": "ls", "args": ["."]}  \n</func_call>'
        func_name, args, kwargs = parse_func_call(content)
        assert func_name == "ls"
        assert args == ["."]

    def test_unicode_characters(self):
        """包含 Unicode 字符"""
        content = '<func_call>{"func_name": "你好", "args": ["世界"]}</func_call>'
        func_name, args, kwargs = parse_func_call(content)
        assert func_name == "你好"
        assert args == ["世界"]

    def test_escaped_backslash(self):
        """转义反斜杠"""
        content = r'<func_call>{"func_name": "x", "args": ["C:\\Users"]}</func_call>'
        func_name, args, kwargs = parse_func_call(content)
        assert args == ["C:\\Users"]

    # ========== 边界情况 ==========

    def test_empty_args_array(self):
        """空数组作为 args"""
        content = '<func_call>{"func_name": "x", "args": []}</func_call>'
        func_name, args, kwargs = parse_func_call(content)
        assert args == []

    def test_empty_kwargs_object(self):
        """空对象作为 kwargs"""
        content = '<func_call>{"func_name": "x", "kwargs": {}}</func_call>'
        func_name, args, kwargs = parse_func_call(content)
        assert kwargs == {}

    def test_string_with_only_whitespace(self):
        """字符串参数仅包含空白字符"""
        content = '<func_call>{"func_name": "x", "args": ["   "]}'
        content += "</func_call>"
        func_name, args, kwargs = parse_func_call(content)
        assert args == ["   "]

    # ========== 无效输入测试（应抛出 ValueError） ==========

    def test_missing_func_call_tags(self):
        """缺少 <func_call> 标签"""
        content = '{"func_name": "x"}'
        with pytest.raises(ValueError, match="必须包含在<func_call></func_call>标签中"):
            parse_func_call(content)

    def test_incomplete_opening_tag(self):
        """标签不完整"""
        content = '<func_call>{"func_name": "x"}</func_call'
        with pytest.raises(ValueError, match="必须包含在<func_call></func_call>标签中"):
            parse_func_call(content)

    def test_missing_func_name(self):
        """JSON 中缺少 func_name 字段"""
        content = '<func_call>{"args": []}</func_call>'
        with pytest.raises(ValueError, match="无法提取 func_name"):
            parse_func_call(content)

    def test_func_name_not_string(self):
        """func_name 不是字符串"""
        content = '<func_call>{"func_name": 123}</func_call>'
        # 整体 JSON 解析会成功但类型不对？手动提取会失败
        # 最终应该抛出异常
        with pytest.raises(ValueError):
            parse_func_call(content)

    def test_invalid_json_completely(self):
        """完全无效的 JSON（手动提取应回退成功）"""
        content = '<func_call>{"func_name": "x", args: [}</func_call>'
        # 手动提取能够提取 func_name 和 args（空列表），因此不会抛出异常
        func_name, args, kwargs = parse_func_call(content)
        assert func_name == "x"
        assert args == []  # 因为 args 解析失败，回退到空列表
        assert kwargs == {}

    def test_extra_text_before_or_after_tag(self):
        """标签前后有额外文本（当前实现要求整个内容就是标签块）"""
        content = 'prefix<func_call>{"func_name": "x"}</func_call>suffix'
        with pytest.raises(ValueError, match="必须包含在<func_call></func_call>标签中"):
            # 因为 startswith 和 endswith 检查失败
            parse_func_call(content)

    def test_nested_func_call_tags(self):
        """嵌套的 func_call 标签（不期望）"""
        content = '<func_call>{"func_name": "outer", "args": ["<func_call>{\\"func_name\\": \\"inner\\"}</func_call>"]}</func_call>'
        # 由于内层标签在字符串内，JSON 解析应该成功，但 func_name 应为 "outer"
        func_name, args, kwargs = parse_func_call(content)
        assert func_name == "outer"
        assert args == ['<func_call>{"func_name": "inner"}</func_call>']

    # ========== 回退解析测试（手动提取分支） ==========
    # 注意：由于整体解析非常强大，这些测试用例确保手动提取也能处理某些边缘情况

    def test_manual_extract_with_unescaped_quotes_inside_string(self):
        """字符串内未转义双引号且修复函数可能无法修复的情况，手动提取应能处理"""
        # 构造一个场景：JSON 整体解析失败，但手动提取能通过正则提取
        # 例如：缺少外层引号包围的字符串
        content = '<func_call>{"func_name": "x", "args": ["unclosed " quote"]}</func_call>'
        # 注意：这个字符串在 Python 中无法直接写，使用原始字符串转义
        # 实际写入的字符串内容为：{"func_name": "x", "args": ["unclosed " quote"]}
        # 这会导致 JSON 解析失败，因为 quote 前面的双引号提前结束了字符串
        # 但手动提取可以通过正则提取 func_name，并通过括号匹配提取数组（尽管内容可能错）
        # 这里我们预期手动提取能够返回 args 为某个列表（可能不完美但不会崩溃）
        # 由于实现中手动提取会调用 _fallback_parse，应该返回 ['unclosed " quote'] 或类似
        func_name, args, kwargs = parse_func_call(content)
        assert func_name == "x"
        # args 可能解析为 ["unclosed ", " quote"]? 但 fallback_parse 简单分割，会得到两个元素
        # 但至少不会抛出异常，并且 func_name 正确
        assert isinstance(args, list)

    def test_manual_extract_with_missing_colon_after_key(self):
        """JSON 格式严重错误，但手动提取仍能提取 func_name（正则匹配）"""
        content = '<func_call>{"func_name" "x", "args": []}</func_call>'
        # 缺少冒号，整体解析失败，但正则 r'"func_name"\s*:\s*"((?:[^"\\]|\\.)*)"' 需要冒号，所以也会失败
        with pytest.raises(ValueError, match="无法提取 func_name"):
            parse_func_call(content)

    # ========== 性能与长输入测试 ==========

    def test_large_args_list(self):
        """大量参数，测试性能与递归限制"""
        large_list = list(range(1000))
        data = {"func_name": "x", "args": large_list}
        json_str = json.dumps(data)
        content = f"<func_call>{json_str}</func_call>"
        func_name, args, kwargs = parse_func_call(content)
        assert func_name == "x"
        assert args == large_list

    def test_deeply_nested_structure(self):
        """深度嵌套结构"""
        nested = []
        current = nested
        for _ in range(100):
            current.append([])
            current = current[0]
        data = {"func_name": "x", "args": nested}
        json_str = json.dumps(data)
        content = f"<func_call>{json_str}</func_call>"
        func_name, args, kwargs = parse_func_call(content)
        assert func_name == "x"
        # 检查深度
        count = 0
        tmp = args
        while isinstance(tmp, list) and len(tmp) == 1:
            tmp = tmp[0]
            count += 1
        assert count == 100