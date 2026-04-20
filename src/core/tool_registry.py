import asyncio
import inspect
import os
import threading
import warnings
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from functools import wraps
from typing import Any, ClassVar, ParamSpec, Self, TypeVar

import nest_asyncio

P = ParamSpec("P")
T = TypeVar("T")
AsyncFunc = Callable[P, Awaitable[T]]
SyncFunc = Callable[P, T]


@dataclass
class ToolInfo:
    """工具信息数据类"""

    name: str
    func: Callable[..., Any]
    params: dict[str, Any]
    doc: str

    def to_markdown(self) -> str:
        """转换为Markdown格式"""
        return f'<func_name="{self.name}" params={extract_params(self.func)} doc="{self.doc}" />'


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


class ToolRegistry:
    """
    工具注册表类(单例模式)

    每个名字对应一个唯一的单例实例
    """

    _instance: ClassVar[Self | None] = None
    _instance_lock: ClassVar[threading.Lock] = threading.Lock()

    def __new__(cls) -> "ToolRegistry":
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

        self._tools: dict[str, ToolInfo] = {}
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

    def register(self, name: str | None = None, doc: str | None = None) -> Callable[[SyncFunc[P, T]], SyncFunc[P, T]]:
        """
        注册同步函数的装饰器

        Args:
            name: 工具名称,默认为函数名
            doc: 文档描述,默认为函数docstring

        Example:
            @registry.register(name="my_tool", doc="这是一个示例工具")
            def example(a: int, b: str = "default") -> str:
                return f"{a}_{b}"
        """

        def decorator(func: SyncFunc[P, T]) -> SyncFunc[P, T]:
            tool_name = name if name is not None else func.__name__
            tool_doc = doc if doc is not None else inspect.getdoc(func) or ""

            self._validate_tool_info(tool_name, tool_doc)

            params = extract_params(func)

            tool_info = ToolInfo(name=tool_name, func=func, params=params, doc=tool_doc)

            self._tools[tool_name] = tool_info

            @wraps(func)
            def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
                return func(*args, **kwargs)

            return wrapper

        return decorator

    def register_function(self, func: Callable[..., Any], name: str | None = None, doc: str | None = None) -> None:
        """
        直接注册函数(非装饰器方式)

        Args:
            func: 要注册的函数
            name: 工具名称,默认为函数名
            doc: 文档描述,默认为函数docstring
        """
        tool_name = name if name is not None else func.__name__
        tool_doc = doc if doc is not None else inspect.getdoc(func) or ""

        self._validate_tool_info(tool_name, tool_doc)

        params = extract_params(func)

        tool_info = ToolInfo(name=tool_name, func=func, params=params, doc=tool_doc)

        self._tools[tool_name] = tool_info

    def _compress_result(self, result: Any) -> Any:
        """压缩过长的结果"""
        if isinstance(result, str):
            if len(result) > self.MAX_RESULT_LENGTH:
                return result[: self.MAX_RESULT_LENGTH] + "... [结果已截断]"
        elif isinstance(result, (list, tuple)):
            if len(result) > self.LIST_TRUNCATE_THRESHOLD:
                return [*list(result[: self.LIST_TRUNCATE_THRESHOLD]), "... [列表已截断]"]
        elif isinstance(result, dict) and len(result) > self.DICT_TRUNCATE_THRESHOLD:
            compressed = {k: result[k] for k in list(result.keys())[: self.DICT_TRUNCATE_THRESHOLD]}
            compressed["..."] = "[字典已截断]"
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
                result = f'<func_name="{tool.name}", errors={e.__class__.__name__}({e})>'

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
                    markdown_lines.append(tool.to_markdown())

        return "\n".join(markdown_lines)

    def list_tools(self) -> dict[str, list[str]]:
        """列出所有已注册的工具"""
        return {"sync": list(self._tools.keys())}

    def get_tool_info(self, name: str) -> ToolInfo | None:
        """获取工具信息"""
        return self._tools.get(name)

    def __repr__(self) -> str:
        return f"ToolRegistry(sync_tools={len(self._tools)})"
