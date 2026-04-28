"""
字符串快照工具 - 统一管理字符串截断逻辑

本模块提供了多种场景下的字符串截断功能,用于生成可读的字符串预览快照.
所有截断逻辑集中在此处,避免代码重复.

场景说明:
- 单个字符串参数: 保留前 27 字符 + "..." (最大 30 字符)
- 整体参数串: 保留前 47 字符 + "..." (最大 50 字符)
- 动态长度: 保留前 max_length-3 字符 + "..."
- 通用截断: 支持自定义后缀
"""


def truncate_string(value: str, max_length: int = 30, suffix: str = "...") -> str:
    """
    通用字符串截断函数

    Args:
        value: 要截断的字符串
        max_length: 最大长度限制,默认 30
        suffix: 截断后添加的后缀,默认 "..."

    Returns:
        截断后的字符串
        - 如果原字符串长度 <= max_length,返回原字符串
        - 否则返回前 (max_length - len(suffix)) 字符 + suffix

    Examples:
        >>> truncate_string("Hello World", 10)
        'Hello W...'
        >>> truncate_string("Short", 10)
        'Short'
        >>> truncate_string("Very Long String", 15, "~~")
        'Very Long S~~'
    """
    if len(value) <= max_length:
        return value

    # 计算保留的字符数
    keep_length = max_length - len(suffix)
    if keep_length <= 0:
        # 如果后缀长度超过最大长度,直接返回后缀
        return suffix

    return value[:keep_length] + suffix


def truncate_single_string(value: str) -> str:
    """
    单个字符串参数截断

    用于格式化显示单个字符串参数值,最多显示 30 个字符.
    超过时保留前 27 个字符 + "..."
    """
    return truncate_string(value, max_length=30, suffix="...")


def truncate_params_string(value: str) -> str:
    """
    整体参数串截断

    用于格式化显示一组参数拼接成的字符串,最多显示 50 个字符.
    超过时保留前 47 个字符 + "..."
    """
    # 最大长度 50,保留前 47 字符 + "..." (len=3)
    return truncate_string(value, max_length=50, suffix="...")


def truncate_for_display(text: str, max_length: int = 70) -> str:
    """
    用于 REPL 显示的一般文本截断

    默认最大长度 70,保留前 67 字符 + "..."
    """
    return truncate_string(text, max_length=max_length, suffix="...")
