import html
import re
import shlex
import warnings

from src.console.commands.command_registry import CommandRegistry
from src.models.commands import CommandParseResult


def parse_input(user_input: str, cmd_register: CommandRegistry, warns: list[str]) -> CommandParseResult:
    """Parse user input, distinguishing commands from tool calls"""
    user_input = user_input.strip()
    parse_result = CommandParseResult(source=user_input, is_command=False, is_func=False)

    if not user_input:
        return parse_result

    if user_input.startswith("/"):
        parts = shlex.split(user_input)
        cmd = parts[0].lower()  # 有`/`的

        for maybe_cmd in cmd_register.list_commands():
            if cmd in maybe_cmd.aliases:
                parse_result.is_command = True
                parse_result.command_type = maybe_cmd.name
                return parse_result

    try:
        # 支持带属性的 func_call 标签
        pattern = r"<func_call\b[^>]*>.*?</func_call>"
        matches = list(re.finditer(pattern, user_input, re.DOTALL))

        for match in matches:
            matched_text = match.group(0)
            try:
                func_name, kwargs = parse_func_call(matched_text, warns)
                if not parse_result.funcs:
                    parse_result.funcs = []
                parse_result.is_func = True
                parse_result.funcs.append((func_name, kwargs))
            except Exception as err:
                warns.append(f"尝试解析单个工具调用时出错:{err!s}")

    except Exception as e:
        warns.append(f"尝试解析输入为工具调用时出错:{e!s}")
        pass

    return parse_result


# noinspection PyBroadException
def parse_func_call(content: str, warns: list[str]) -> tuple[str, dict]:
    """
    从 <func_call> 标签中提取函数名和参数,使用健壮的回退机制.
    """
    warnings.warn(
        "当参数存在`<func_call`字符串时, 会导致无法正确解析工具调用, 需要避免AI在参数输入这个",
        DeprecationWarning,
        stacklevel=2,
    )
    # 提取标签内内容
    inner = re.sub(r"^<func_call\b", "", content)
    inner = re.sub(r"</func_call>$", "", inner).strip()

    # 提取函数名 — 优先使用 name 属性格式 (标准格式)
    func_call_attr_match = re.match(r'<func_call\s+name="([^"]*)"\s*>', content)
    if func_call_attr_match:
        func_name = func_call_attr_match.group(1).strip()
    else:
        # 尝试标准 func_name 标签
        func_name_match = re.search(r"<func_name>(.*?)</func_name>", inner, re.DOTALL)

        if func_name_match:
            func_name = func_name_match.group(1).strip()
        else:
            # 尝试非标准 func_name 标签(带 name 属性)
            func_name_attr_match = re.search(r'<func_name\s+name="([^"]*)"\s*>\s*</func_name>', inner, re.DOTALL)
            if func_name_attr_match:
                warns.append("检测到非标准格式:func_name 标签包含 name 属性,尝试从属性中提取函数名")
                func_name = func_name_attr_match.group(1).strip()
            else:
                raise ValueError("未找到<func_name></func_name>标签,无法提取函数名")

    if not func_name:
        raise ValueError("函数名为空,无法提取有效的函数名")

    # 提取所有参数
    kwargs = {}

    # 标准格式:<param name="xxx">value</param>
    # 使用非贪婪匹配,但确保能匹配到正确的 </param> 结束标签
    standard_param_pattern = r'<param\s+name="([^"]+)"\s*>(.*?)</param>'
    for match in re.finditer(standard_param_pattern, inner, re.DOTALL):
        param_name = match.group(1).strip()
        param_value = match.group(2).strip()
        kwargs[param_name] = unescape(param_value, warns)

    # 属性格式:<param name="xxx" value="yyy"></param> 或 <param name="xxx" value="yyy" />
    attr_param_pattern = r'<param\s+name="([^"]+)"\s+value="([^"]*)"\s*/?>'
    for match in re.finditer(attr_param_pattern, inner, re.DOTALL):
        param_name = match.group(1).strip()
        param_value = match.group(2).strip()

        if param_name not in kwargs:  # 避免覆盖已有的同名参数
            kwargs[param_name] = unescape(param_value, warns)
            warns.append(f"检测到非标准格式:参数 '{param_name}' 使用 value 属性而非标签文本")
        else:
            warns.append(f"参数 '{param_name}' 已存在,跳过属性格式的值")

    # 混合格式检查:如果两种格式都存在,记录警告
    has_standard = bool(re.search(standard_param_pattern, inner, re.DOTALL))
    has_attr = bool(re.search(attr_param_pattern, inner, re.DOTALL))
    if has_standard and has_attr:
        warns.append("检测到混合参数格式(标签文本和属性值),可能存在不一致")

    return func_name, kwargs


def unescape(context: str, warns: list[str]) -> str:
    """还原参数中的转义字符"""
    try:
        return html.unescape(context)
    except Exception as err:
        warns.append(f"转义HTML实体符号时出错: {err}")
    return context
