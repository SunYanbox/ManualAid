import inspect
from collections.abc import Callable
from typing import Any

from src.workspace.workspace import Workspace


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

    def to_markdown(self) -> str:
        """转换为Markdown格式"""
        return (
            f'<func_name="{self.name}">\n<params>{self.params}</params>\n'
            + f'<doc>{self.doc}</doc>\n</func_name="{self.name}">'
        )

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
