import json
from typing import Any


def parse_func_call(content: str) -> tuple[str, list[Any], dict[str, Any]]:
    """
    提取函数调用名称与参数
    """
    if not content.startswith("<func_call>") or not content.endswith("</func_call>"):
        raise ValueError("函数调用json必须包含在<func_call></func_call>标签中")
    result: dict = json.loads(content.replace("<func_call>", "").replace("</func_call>", ""))
    func_name: str = result["func_name"]
    func_args: list = result.get("args", [])
    func_kwargs: dict = result.get("kwargs", {})
    return func_name, func_args, func_kwargs
