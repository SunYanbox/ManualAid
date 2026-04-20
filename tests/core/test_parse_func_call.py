import json

import pytest

from src.core.parse_func_call import parse_func_call


def test_parse_func_call_basic():
    content = '<func_call>{"func_name": "test_func", "args": [1, 2], "kwargs": {"key": "value"}}</func_call>'
    func_name, args, kwargs = parse_func_call(content)

    assert func_name == "test_func"
    assert args == [1, 2]
    assert kwargs == {"key": "value"}


def test_parse_func_call_empty_args():
    content = '<func_call>{"func_name": "empty_func", "args": [], "kwargs": {}}</func_call>'
    func_name, args, kwargs = parse_func_call(content)

    assert func_name == "empty_func"
    assert args == []
    assert kwargs == {}


def test_parse_func_call_missing_tags():
    content = '{"func_name": "test_func", "args": [], "kwargs": {}}'

    with pytest.raises(ValueError) as exc_info:
        parse_func_call(content)

    assert "函数调用json必须包含在<func_call></func_call>标签中" in str(exc_info.value)


def test_parse_func_call_invalid_json():
    content = '<func_call>{"func_name": "test_func", args: [1], kwargs: {}}</func_call>'

    with pytest.raises(json.JSONDecodeError) as exc_info:
        parse_func_call(content)

    assert "Expecting property name enclosed in double quotes" in str(exc_info.value)


def test_parse_func_call_only_opening_tag():
    content = '<func_call>{"func_name": "test_func", "args": [], "kwargs": {}}'

    with pytest.raises(ValueError) as exc_info:
        parse_func_call(content)

    assert "函数调用json必须包含在<func_call></func_call>标签中" in str(exc_info.value)


def test_parse_func_call_only_closing_tag():
    content = '{"func_name": "test_func", "args": [], "kwargs": {}}</func_call>'

    with pytest.raises(ValueError) as exc_info:
        parse_func_call(content)

    assert "函数调用json必须包含在<func_call></func_call>标签中" in str(exc_info.value)
