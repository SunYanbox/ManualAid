from src.core.input_parser import unescape


def test_unescape():
    source = "<func_call>"
    source1 = "&lt;func_call&gt;"
    warns = []
    assert unescape(source, warns) == source, "Html转义改变了没有转义字符的字符串"
    assert unescape(source1, warns) == source, "Html没有正确转义转义字符"
