import inspect
from collections.abc import Callable
from typing import Any

from src.workspace.workspace import Workspace


def _build_param_doc(name: str, params: dict[str, Any]) -> str:
    """根据名字和参数生成参数的xml标签"""
    result = f'<param name="{name}"'
    if "annotation" in params:
        result += f' type="{params["annotation"]}"'
    else:
        result += " type=unknown"
    if "default" in params:
        result += f" default={params['default']}"
    result += " />"
    return result


def convert_param_type(value: str, expected_type: str) -> Any:
    """
    根据期望的类型注解转换参数值

    Args:
        value: 原始字符串值
        expected_type: 期望的类型注解字符串(如 '<class 'int'>' 或 'int')

    Returns:
        转换后的值
    """
    # 提取类型名称
    type_name = expected_type.lower()
    if "<class " in type_name:
        # 提取 <class 'int'> 中的 int
        import re

        match = re.search(r"'(\w+)'", expected_type)
        if match:
            type_name = match.group(1).lower()

    # 类型转换
    if type_name in ("int", "integer"):
        try:
            return int(value)
        except ValueError:
            return value
    elif type_name in ("float", "double"):
        try:
            return float(value)
        except ValueError:
            return value
    elif type_name in ("bool", "boolean"):
        return value.lower() in ("true", "1", "yes", "on")
    elif type_name in ("list", "tuple"):
        # 简单列表解析 [1,2,3] 或 ["a","b"]
        if value.startswith("[") and value.endswith("]"):
            import json

            try:
                return json.loads(value)
            except json.JSONDecodeError:
                # 简单分割
                inner = value[1:-1].strip()
                if inner:
                    return [item.strip().strip("\"'") for item in inner.split(",")]
                return []
        return value
    elif type_name in ("dict", "dictionary"):
        # 简单字典解析 {"key":"value"}
        if value.startswith("{") and value.endswith("}"):
            import json

            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return value
    else:
        # 字符串或其他类型
        return value


class BaseTool:
    def __init__(
        self,
        workspace: Workspace,
        name: str = "",
        doc: str = "",
        read_permission: bool = True,
        write_permission: bool = False,
    ):
        self.workspace = workspace
        # 排除无效工具
        if name is None or len(name) == 0:
            raise ValueError(f"注册工具时{self.__class__.__name__}的名称没有有效值")
        if doc is None or len(doc) == 0:
            raise ValueError(f"注册工具时{self.__class__.__name__}的文档没有有效值")
        # 读取权限
        self.read_permission: bool = read_permission
        # 写入权限
        self.write_permission: bool = write_permission
        self.name: str = name
        self.doc: str = doc
        self.func: Callable[..., Any] | None = None
        self.params: dict[str, Any] | None = None

    def to_doc(self) -> str:
        """转换为模型可读文档格式"""
        if self.params is not None and len(self.params) > 0:
            required_params = []
            param_docs = []
            for name, param in self.params.items():
                if param.get("required", False):
                    required_params.append(name)
                param_docs.append(_build_param_doc(name, param))
            param_doc = (
                f"<params>\n{'\n'.join(param_docs)}\n<required>{','.join(required_params)}</required>\n</params>"
            )
        else:
            param_doc = "<No any params />"
        return f'<func_name="{self.name}">\n{param_doc}\n' + f"<doc>{self.doc}</doc>\n</func_name>"

    @staticmethod
    def extract_params(func: Callable[..., Any]) -> dict[str, Any]:
        """提取函数参数信息"""
        sig = inspect.signature(func)
        params = {}
        for param_name, param in sig.parameters.items():
            if param_name not in ("self", "cls"):
                param_info = {
                    "required": param.default == inspect.Parameter.empty,
                    "annotation": str(param.annotation) if param.annotation != inspect.Parameter.empty else "Any",
                }
                if param.default != inspect.Parameter.empty:
                    param_info["default"] = repr(param.default)
                params[param_name] = param_info
        return params

    def convert_args(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        """
        根据参数类型注解转换参数值

        Args:
            kwargs: 原始参数字典(值可能都是字符串)

        Returns:
            转换类型后的参数字典
        """
        if not self.params:
            return kwargs

        converted = {}
        for param_name, param_value in kwargs.items():
            if param_name in self.params:
                expected_type = self.params[param_name].get("annotation", "Any")
                converted[param_name] = convert_param_type(str(param_value), expected_type)
            else:
                converted[param_name] = param_value

        return converted
