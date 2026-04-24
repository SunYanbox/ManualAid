import re


# noinspection PyBroadException
def parse_func_call(content: str) -> tuple[str, dict]:
    """
    从 <func_call> 标签中提取函数名和参数,使用整体 JSON 解析 + 健壮的回退机制.
    """
    if not content.startswith("<func_call>") or not content.endswith("</func_call>"):
        raise ValueError("函数调用名称与参数必须包含在<func_call></func_call>标签中")

    # 提取标签内内容
    inner = re.sub(r"^<func_call>", "", content)
    inner = re.sub(r"</func_call>$", "", inner).strip()

    # 提取函数名
    func_name_match = re.search(r"<func_name>(.*?)</func_name>", inner, re.DOTALL)
    if not func_name_match:
        raise ValueError("未找到<func_name></func_name>标签,无法提取函数名")
    func_name = func_name_match.group(1).strip()

    # 提取所有参数
    kwargs = {}
    param_pattern = r'<param name="([^"]+?)">(.*?)</param>'
    for match in re.finditer(param_pattern, inner, re.DOTALL):
        param_name = match.group(1).strip()
        param_value = match.group(2).strip()
        kwargs[param_name] = param_value

    return func_name, kwargs
