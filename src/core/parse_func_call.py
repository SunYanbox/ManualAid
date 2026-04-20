import json
import re
from typing import Any


# noinspection PyBroadException
def parse_func_call(content: str) -> tuple[str, list, dict]:
    """
    从 <func_call> 标签中提取函数名和参数,使用整体 JSON 解析 + 健壮的回退机制.
    """
    if not content.startswith("<func_call>") or not content.endswith("</func_call>"):
        raise ValueError("函数调用json必须包含在<func_call></func_call>标签中")

    # 提取标签内内容
    inner = re.sub(r"^<func_call>", "", content)
    inner = re.sub(r"</func_call>$", "", inner).strip()

    # 优先尝试整体 JSON 解析(带修复)
    try:
        data = _robust_json_parse(inner)
        if not isinstance(data, dict):
            raise ValueError("顶层 JSON 必须是对象")
        if "func_name" not in data:
            raise ValueError("缺少 func_name 字段")
        func_name = data["func_name"]
        if not isinstance(func_name, str):
            raise ValueError(f"func_name 必须是字符串,实际类型: {type(func_name).__name__}")
        args = data.get("args", [])
        kwargs = data.get("kwargs", {})
        if not isinstance(args, list):
            args = []
        if not isinstance(kwargs, dict):
            kwargs = {}
        return func_name, args, kwargs
    except Exception:
        # 整体解析失败,降级到手动提取(兼容旧逻辑)
        return _manual_extract(inner)


# noinspection PyBroadException
def _robust_json_parse(s: str) -> Any:
    """
    健壮的 JSON 解析:先直接解析,失败则修复常见问题后再解析.
    返回任意 JSON 类型(dict, list, str, int, float, bool, None).
    """
    # 1. 直接解析
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass

    # 2. 尝试 ast.literal_eval(支持单引号等)
    try:
        import ast

        obj = ast.literal_eval(s)
        # ast.literal_eval 可以解析 Python 字面量,也符合 JSON 语义
        return obj
    except Exception:
        pass

    # 3. 修复字符串内未转义的双引号和换行符
    fixed = _fix_unescaped_quotes(s)
    try:
        return json.loads(fixed)
    except json.JSONDecodeError as e:
        raise ValueError(f"无法解析 JSON,即使修复后仍失败: {e}") from e


def _fix_unescaped_quotes(s: str) -> str:
    """
    修复 JSON 字符串值内部未转义的双引号和换行符.
    使用状态机,仅在字符串内部(非转义状态)进行替换.
    不破坏已有的合法转义序列(如 \\, \", \n 等).
    """
    result = []
    in_string = False
    escape = False
    i = 0
    length = len(s)
    while i < length:
        ch = s[i]
        if escape:
            # 当前字符已被转义,原样保留
            result.append(ch)
            escape = False
            i += 1
            continue

        if ch == "\\":
            # 转义字符开始,保留反斜杠,并标记转义状态
            result.append(ch)
            escape = True
            i += 1
            continue

        if ch == '"':
            if not in_string:
                # 进入字符串
                in_string = True
                result.append(ch)
            else:
                # 字符串内部的引号需要转义
                result.append('\\"')
            i += 1
            continue

        if ch == "\n" and in_string:
            # 字符串内的换行符转义为 \n
            result.append("\\n")
            i += 1
            continue

        # 普通字符
        result.append(ch)
        i += 1

    return "".join(result)


def _manual_extract(inner: str) -> tuple[str, list, dict]:
    """
    手动提取函数名和参数(回退方案),使用正则和手动括号匹配.
    修复了字符串内括号的误判,并增强 func_name 正则.
    """
    # 1. 提取 func_name,支持转义双引号
    func_name_match = re.search(r'"func_name"\s*:\s*"((?:[^"\\]|\\.)*)"', inner)
    if not func_name_match:
        raise ValueError("无法提取 func_name")
    func_name = func_name_match.group(1)

    # 2. 提取 args 数组
    args = _extract_json_array(inner, "args")
    # 3. 提取 kwargs 对象
    kwargs = _extract_json_object(inner, "kwargs")

    return func_name, args, kwargs


# noinspection PyBroadException
def _extract_json_array(text: str, key: str) -> list:
    """
    从 JSON 文本中提取指定 key 的数组值,使用括号匹配并忽略字符串内的括号.
    """
    # 注意:f-string 中需要双大括号 {{ 表示字面量 {
    key_pattern = re.compile(rf'"{key}"\s*:\s*\[')
    match = key_pattern.search(text)
    if not match:
        return []

    start = match.end() - 1  # 指向 '[' 的位置
    bracket_count = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"' and not escape:
            in_string = not in_string
            continue
        if not in_string:
            if ch == "[":
                bracket_count += 1
            elif ch == "]":
                bracket_count -= 1
                if bracket_count == 0:
                    array_str = text[start : i + 1]
                    try:
                        # 这里期望解析出 list 类型
                        parsed = _robust_json_parse(array_str)
                        if isinstance(parsed, list):
                            return parsed
                        else:
                            # 如果解析结果不是 list,尝试回退解析
                            return _fallback_parse(array_str)
                    except Exception:
                        return _fallback_parse(array_str)
    return []


# noinspection PyBroadException
def _extract_json_object(text: str, key: str) -> dict:
    """
    从 JSON 文本中提取指定 key 的对象值,使用大括号匹配并忽略字符串内的括号.
    """
    # 使用双大括号 {{ 在 f-string 中表示字面量 {
    key_pattern = re.compile(rf'"{key}"\s*:\s*{{')
    match = key_pattern.search(text)
    if not match:
        return {}

    start = match.end() - 1  # 指向 '{' 的位置
    brace_count = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"' and not escape:
            in_string = not in_string
            continue
        if not in_string:
            if ch == "{":
                brace_count += 1
            elif ch == "}":
                brace_count -= 1
                if brace_count == 0:
                    obj_str = text[start : i + 1]
                    try:
                        parsed = _robust_json_parse(obj_str)
                        if isinstance(parsed, dict):
                            return parsed
                        else:
                            return {}
                    except Exception:
                        return {}
    return {}


def _fallback_parse(part_str: str) -> Any:
    """
    极简回退解析:匹配简单数组(字符串、数字、布尔值、None).
    如果无法解析,返回空列表.
    """
    part_str = part_str.strip()
    if not (part_str.startswith("[") and part_str.endswith("]")):
        return []
    # 去掉外层括号
    inner = part_str[1:-1].strip()
    if not inner:
        return []
    items = []
    # 简单的逗号分割,不考虑嵌套(仅用于最坏情况)
    # 使用正则匹配字面量
    pattern = r'"([^"\\]*(?:\\.[^"\\]*)*)"|\'([^\'\\]*(?:\\.[^\'\\]*)*)\'|(\d+(?:\.\d+)?)|(true|false|null)'
    for match in re.finditer(pattern, inner):
        if match.group(1) is not None:
            items.append(match.group(1))
        elif match.group(2) is not None:
            items.append(match.group(2))
        elif match.group(3) is not None:
            num = match.group(3)
            items.append(float(num) if "." in num else int(num))
        elif match.group(4) is not None:
            val = match.group(4)
            if val == "true":
                items.append(True)
            elif val == "false":
                items.append(False)
            elif val == "null":
                items.append(None)
    return items
