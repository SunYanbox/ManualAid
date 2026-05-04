import asyncio
import copy
import inspect
import json
import os
import threading
import time
import warnings
from collections.abc import Awaitable, Callable
from typing import Any, ClassVar, ParamSpec, Self, TypeVar

import nest_asyncio

from src.console.result_manager import _to_string
from src.utils.string_snapshot import truncate_string
from src.workspace.tools.base_tool import BaseTool
from src.workspace.workspace import Workspace

P = ParamSpec("P")
T = TypeVar("T")
AsyncFunc = Callable[P, Awaitable[T]]
SyncFunc = Callable[P, T]


class ToolRegistry:
    """
    工具注册表类(单例模式)

    每个名字对应一个唯一的单例实例
    """

    _instance: ClassVar[Self | None] = None
    _instance_lock: ClassVar[threading.Lock] = threading.Lock()

    def __new__(cls) -> ToolRegistry:
        """确保每个名字只有一个实例(线程安全)"""
        with cls._instance_lock:
            if cls._instance is None:
                instance = super().__new__(cls)
                instance._initialized = False
                cls._instance = instance
        return cls._instance

    def __init__(self):
        """初始化注册表"""
        if self._initialized:
            return

        self._tools: dict[str, BaseTool] = {}
        self._current_session_id: int | None = None
        self._workspace: Workspace | None = None
        self._tool_categories: dict[str, str] = {}
        self._initialized = True

        # 配置常量 - 从环境变量读取,带默认值
        self.MAX_DOC_LENGTH = int(os.getenv("TOOL_MAX_DOC_LENGTH", "360"))
        self.MAX_FUNC_NAME_LENGTH = int(os.getenv("TOOL_MAX_FUNC_NAME_LENGTH", "80"))
        self.MAX_RESULT_LENGTH = int(os.getenv("TOOL_MAX_RESULT_LENGTH", "30000"))
        self.LIST_TRUNCATE_THRESHOLD = int(os.getenv("TOOL_LIST_TRUNCATE_THRESHOLD", "100"))
        self.DICT_TRUNCATE_THRESHOLD = int(os.getenv("TOOL_DICT_TRUNCATE_THRESHOLD", "100"))

        # 验证配置值
        self._validate_config()

    def _validate_config(self) -> None:
        """验证配置值确保在合理范围内"""
        if self.MAX_RESULT_LENGTH < 10:
            warnings.warn(
                f"TOOL_MAX_RESULT_LENGTH 过小({self.MAX_RESULT_LENGTH}),建议至少为100", UserWarning, stacklevel=2
            )
            self.MAX_RESULT_LENGTH = 100

        if self.LIST_TRUNCATE_THRESHOLD < 10:
            warnings.warn(
                f"TOOL_LIST_TRUNCATE_THRESHOLD 过小({self.LIST_TRUNCATE_THRESHOLD}),建议至少为50",
                UserWarning,
                stacklevel=2,
            )
            self.LIST_TRUNCATE_THRESHOLD = 50

        if self.DICT_TRUNCATE_THRESHOLD < 10:
            warnings.warn(
                f"TOOL_DICT_TRUNCATE_THRESHOLD 过小({self.DICT_TRUNCATE_THRESHOLD}),建议至少为50",
                UserWarning,
                stacklevel=2,
            )
            self.DICT_TRUNCATE_THRESHOLD = 50

    def _validate_tool_info(self, name: str, doc: str) -> None:
        """验证工具信息并发出警告"""
        if not doc:
            warnings.warn(f"工具 '{name}' 缺少文档化描述", UserWarning, stacklevel=3)
        elif len(doc) > self.MAX_DOC_LENGTH:
            warnings.warn(f"工具 '{name}' 的文档描述超过 {self.MAX_DOC_LENGTH} 字符", UserWarning, stacklevel=3)

        if len(name) > self.MAX_FUNC_NAME_LENGTH:
            warnings.warn(f"工具名称 '{name}' 超过 {self.MAX_FUNC_NAME_LENGTH} 字符", UserWarning, stacklevel=3)

    def _set_tool_category(self, tool: BaseTool) -> None:
        """根据工具的 write_permission 属性设置分类."""
        if tool.name == "git":
            self._tool_categories[tool.name] = "dangerous"
        elif tool.write_permission:
            self._tool_categories[tool.name] = "write"
        else:
            self._tool_categories[tool.name] = "query"

    def register(self, workspace: Workspace) -> None:
        """为工作区注册工具"""
        from src.workspace.tools.edit_tool import EditTool
        from src.workspace.tools.exact_search_tool import ExactSearchTool
        from src.workspace.tools.git_tool import GitTool
        from src.workspace.tools.glob_tool import GlobTool
        from src.workspace.tools.ls_tool import LsTool
        from src.workspace.tools.read_tool import ReadTool
        from src.workspace.tools.regex_search_tool import RegexSearchTool
        from src.workspace.tools.stat_tool import StatTool
        from src.workspace.tools.symbol_ref_tool import SymbolRefTool
        from src.workspace.tools.write_tool import WriteTool

        self._workspace = workspace

        for cls in (
            ExactSearchTool,
            GlobTool,
            LsTool,
            ReadTool,
            RegexSearchTool,
            WriteTool,
            StatTool,
            SymbolRefTool,
            EditTool,
            GitTool,
        ):
            try:
                tool = cls(workspace)
                if tool.func is None or tool.params is None:
                    warnings.warn(f"工具{tool.name}没有注册功能回调和参数", stacklevel=2)
                    continue
                self._tools[tool.name] = tool
                self._set_tool_category(tool)
            except ValueError:
                pass

    def _compress_result(self, result: Any) -> Any:
        """压缩过长的结果"""
        result_length = len(result)
        if isinstance(result, str):
            if result_length > self.MAX_RESULT_LENGTH:
                return (
                    result[: self.MAX_RESULT_LENGTH]
                    + f"... [字符串结果已截断 显示的字符数: {self.LIST_TRUNCATE_THRESHOLD} / {result_length}]"
                )
        elif isinstance(result, (list, tuple)):
            if result_length > self.LIST_TRUNCATE_THRESHOLD:
                return [
                    *list(result[: self.LIST_TRUNCATE_THRESHOLD]),
                    f"... [列表已截断 显示的项: {self.LIST_TRUNCATE_THRESHOLD} / {result_length}]",
                ]
        elif isinstance(result, dict) and result_length > self.DICT_TRUNCATE_THRESHOLD:
            compressed = {k: result[k] for k in list(result.keys())[: self.DICT_TRUNCATE_THRESHOLD]}
            compressed["..."] = f"[字典已截断 显示的项: {self.DICT_TRUNCATE_THRESHOLD} / {result_length}]"
            return compressed

        return result

    def execute(self, func_name: str, *args: Any, **kwargs: Any) -> Any:
        """
        执行工具函数

        Args:
            func_name: 工具名称
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            函数执行结果(自动压缩过长的结果)
        """
        if func_name in self._tools:
            tool = self._tools[func_name]
            kwargs = tool.convert_args(kwargs)

            start_time = time.perf_counter()
            status = "success"
            try:
                if inspect.iscoroutinefunction(tool.func):
                    coro = tool.func(*args, **kwargs)
                    # 已有事件循环
                    try:
                        loop = asyncio.get_running_loop()
                        nest_asyncio.apply()
                        result = loop.run_until_complete(coro)
                    except RuntimeError:  # pragma: no cover  // pytest内置事件循环, 测不到这里
                        # 没有运行中的事件循环
                        result = asyncio.run(coro)
                else:
                    # 同步函数
                    result = tool.func(*args, **kwargs)
            except Exception as e:
                status = "error"
                result = f'<func_name="{tool.name}", errors={e.__class__.__name__}({e})>'

            duration_ms = (time.perf_counter() - start_time) * 1000
            self._log_tool_call(func_name, kwargs, duration_ms, status)
            self._record_tool_call_summary(func_name, kwargs, result)

            return self._compress_result(result)
        else:
            raise ValueError(f"未找到工具: {func_name}")

    def generate_markdown(self) -> str:
        """
        生成工具的Markdown文档

        Returns:
            Markdown格式的工具文档
        """
        markdown_lines = []

        if self._tools:
            markdown_lines.append("## 工具\n")
            for tool in self._tools.values():
                if tool.doc:  # 只包含有文档描述的工具
                    markdown_lines.append(tool.to_doc())

        return "\n".join(markdown_lines)

    def list_tools(self) -> dict[str, list[str]]:
        """列出所有已注册的工具"""
        return {"sync": list(self._tools.keys())}

    def get_tool_info(self, name: str) -> BaseTool | None:
        """获取工具信息"""
        return self._tools.get(name)

    def set_session_id(self, session_id: int) -> None:
        """设置当前会话 ID"""
        self._current_session_id = session_id

    @staticmethod
    def _compute_kwargs_json(kwargs: dict) -> str:
        truncated = copy.deepcopy(kwargs)
        for key, value in truncated.items():
            if isinstance(value, str) and len(value) > 256:
                truncated[key] = truncate_string(value, max_length=256, suffix="...")
        return json.dumps(truncated, sort_keys=True, default=str)

    def _log_tool_call(self, func_name: str, kwargs: dict, duration_ms: float, status: str) -> str | None:
        session_id = getattr(self, "_current_session_id", None)
        if session_id is None:
            return None
        try:
            kwargs_json = self._compute_kwargs_json(kwargs)
            workspace = getattr(self, "_workspace", None)
            if workspace is not None:
                # Determine audit_status based on tool category
                category = self._tool_categories.get(func_name, "query")
                audit_status = "none"

                if category == "dangerous" and func_name == "git":
                    # Git: check if the specific command is safe
                    from src.workspace.tools.git_tool import GitTool

                    command_str = kwargs.get("command_str", "")
                    if not GitTool.is_safe_command(command_str):
                        audit_status = "PENDING_AUDIT"
                elif category == "write":
                    audit_status = "none"  # Snapshot has its own PENDING_AUDIT

                workspace.db.log_tool_call(
                    session_id,
                    func_name,
                    kwargs_json,
                    duration_ms=duration_ms,
                    status=status,
                    audit_status=audit_status,
                )
        except Exception:
            pass
        return f"ToolRegistry(sync_tools={len(self._tools)})"

    def _record_tool_call_summary(self, func_name: str, kwargs: dict, result: Any) -> None:
        session_id = getattr(self, "_current_session_id", None)
        if session_id is None:
            return

        # Exclude write tools
        tool = self._tools.get(func_name)
        if tool is not None and tool.write_permission:
            return

        try:
            kwargs_json = self._compute_kwargs_json(kwargs)
            workspace = getattr(self, "_workspace", None)
            if workspace is not None:
                result_str = _to_string(result)
                workspace.db.record_tool_call_summary(session_id, func_name, kwargs_json, result_str)
        except Exception:
            pass
