from __future__ import annotations

import time
from typing import TYPE_CHECKING

from src.console.result_manager import ResultManager
from src.console.ui.widgets.tools_result_widget import ToolsResultWidget
from src.constants.files import EXTENSION_TO_LANGUAGE
from src.models.commands import CommandParseResult
from src.models.tools.tool_result_collection import ToolResultCollection
from src.utils.string_snapshot import truncate_for_display, truncate_single_string


def _detect_language(func_name: str, func_kwargs: dict) -> str | None:
    """Detect language for syntax highlighting"""
    if "read" not in func_name:
        return None

    file_path = ""
    if "file_path" in func_kwargs:
        file_path = func_kwargs["file_path"]

    ext_map = EXTENSION_TO_LANGUAGE

    for ext, lang in ext_map.items():
        if file_path.lower().endswith(ext):
            return lang

    return "text"


if TYPE_CHECKING:
    from src.core.tool_registry import ToolRegistry


class ToolHandler:
    """Handler for processing tool calls"""

    def __init__(
        self,
        tool_registry: ToolRegistry,
        result_manager: ResultManager,
        console,
    ):
        self.tool_registry = tool_registry
        self.result_manager = result_manager
        self.console = console

    def handle(self, parsed_input: CommandParseResult) -> bool:
        """Handle a parsed tool call input

        Args:
            parsed_input: CommandParseResult from input_parser

        Returns:
            True if handled successfully, False otherwise
        """
        if parsed_input.is_command:
            return False

        collection: ToolResultCollection = ToolResultCollection()

        for func_name, func_kwargs in parsed_input.funcs:
            parms: str = f"{{{func_kwargs}"

            # 避免多参数工具的返回值过于占上下文
            if len(parms) > 120:
                parms = parms[:117] + "..."

            parms += "}"

            start = time.perf_counter()

            # 执行
            response = self.tool_registry.execute(func_name, **func_kwargs)

            collection.add(func_name, time.perf_counter() - start, kwargs=func_kwargs, result=response.response)

        result = ""

        for results in collection.results.values():
            for _result in results:
                result += _result[1]

        tool_names = truncate_for_display(",".join(collection.tools()))

        self.result_manager.add(tool_names, result)

        tool_result_widget = ToolsResultWidget()
        tool_result_widget.set_collection(collection)

        self.console.print_collapsible_with_widget(truncate_single_string(f"调用工具结果 | {tool_names}") + f" | {time.ctime(time.time())}", tool_result_widget)

        return True
