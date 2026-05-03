import inspect
from collections.abc import Callable
from pathlib import Path
from typing import Any

from src.core.file_tracker import FileTracker
from src.workspace.workspace import Workspace


def build_param_doc(name: str, params: dict[str, Any]) -> str:
    """Generate a concise XML parameter doc."""
    from src.constants.prompts import clean_type_annotation

    result = f'<param name="{name}"'
    if "annotation" in params:
        result += f' type="{clean_type_annotation(params["annotation"])}"'
    else:
        result += ' type="string"'
    if params.get("required", False):
        result += ' required="true"'
    else:
        result += ' required="false"'
    if "default" in params:
        result += f' default="{params["default"]}"'
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
        lines = [f'<func_name="{self.name}">', f"    <description>{self.doc}</description>"]
        if self.params and len(self.params) > 0:
            lines.append("    <params>")
            for name, param in self.params.items():
                lines.append(f"        {build_param_doc(name, param)}")
            lines.append("    </params>")
        else:
            lines.append("    <params><!-- 此工具不需要参数 --></params>")
        lines.append("</func_name>")
        return "\n".join(lines)

    def to_func_call(self) -> str:
        """将工具转换为标准格式"""
        func_call: str = f'<func_call name="{self.name}">\n'
        for name, params in self.params.items():
            func_call += (
                f'    <param name="{name}">'
                + ("" if "default" not in params else str(params.get("default")))
                + "</param>\n"
            )
        func_call += "</func_call>"
        return func_call

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

    def _record_read_meta(self, resolved_path: Path) -> None:
        try:
            meta = FileTracker.get_file_meta(resolved_path)
            if meta:
                session_id = self.workspace._current_session_id
                if session_id is not None:
                    rel_path = str(resolved_path.relative_to(self.workspace.root_path))
                    self.workspace.db.record_file_read(
                        session_id, rel_path, meta["mtime"], meta["size"], meta["checksum"]
                    )
        except Exception:
            pass

    def _validate_mtime(self, resolved_path: Path) -> str | None:
        """校验文件自上次读取后是否被外部修改."""
        if not resolved_path.exists():
            return None

        session_id = self.workspace._current_session_id
        if session_id is None:
            return None

        rel_path = str(resolved_path.relative_to(self.workspace.root_path))
        record = self.workspace.db.get_file_read_record(session_id, rel_path)
        if record is None:
            return None

        stored_mtime = record[3]
        current_mtime = resolved_path.stat().st_mtime

        if abs(current_mtime - stored_mtime) > 0.001:
            return (
                f"ERROR: FILE_MODIFIED_EXTERNALLY - "
                f'The file "{rel_path}" was modified externally since last read. '
                f'Please re-read the file with the "read" tool before editing it.'
            )
        return None

    @staticmethod
    def _generate_diff(old_content: str, new_content: str, file_path: str) -> str:
        import difflib

        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)
        diff = difflib.unified_diff(old_lines, new_lines, fromfile=f"a/{file_path}", tofile=f"b/{file_path}")
        return "".join(diff)

    @staticmethod
    def handle_tool_exceptions(func):
        """工具方法异常处理装饰器."""
        from functools import wraps

        from src.models.tool_error_response import ToolErrorResponse
        from src.workspace.path_validator import PathNotFoundError, WorkspaceBoundaryError

        @wraps(func)
        def wrapper(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except PathNotFoundError as err1:
                return ToolErrorResponse(self.__class__.__name__, err1).to_str()
            except WorkspaceBoundaryError as err2:
                return ToolErrorResponse(self.__class__.__name__, err2).to_str()
            except PermissionError as err3:
                return ToolErrorResponse(self.__class__.__name__, err3).to_str()
            except Exception as err:
                return ToolErrorResponse(self.__class__.__name__, err).to_str()

        return wrapper
