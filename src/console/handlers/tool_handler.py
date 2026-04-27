"""Tool handler for executing tool calls"""

import json
import os
from typing import TYPE_CHECKING, Any

from src.console.ui.interactive_viewer import add_to_viewer, run_viewer
from src.constants.files import EXTENSION_TO_LANGUAGE
from src.models.commands import CommandParseResult
from src.utils.string_snapshot import truncate_params_string, truncate_single_string

if TYPE_CHECKING:
    from src.console.result_manager import ResultManager
    from src.core.tool_registry import ToolRegistry


def _auto_view_if_enabled() -> None:
    """Auto-run viewer if enabled"""
    auto_view = os.getenv("MANUALAID_AUTO_VIEW", "").lower() in ("true", "1", "yes", "on")
    if auto_view:
        run_viewer()


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


def _format_tool_params(kwargs: dict) -> str:
    """Format tool parameters as concise string"""
    parts = []

    # Keyword arguments
    for key, value in kwargs.items():
        if isinstance(value, str):
            parts.append(f'{key}="{truncate_single_string(value)}"')
        else:
            parts.append(f"{key}={value}")

    if not parts:
        return "no parameters"

    params_str = truncate_params_string(", ".join(parts))

    return params_str


def _create_result_title(index: int, func_name: str, kwargs: dict, lines_count: int) -> str:
    """Create result title with Rich markup"""
    params_str = _format_tool_params(kwargs)
    return (
        f"[bold cyan]##{index}[/bold cyan] [bold green]{func_name}[/bold green]([dim]{params_str}[/dim])"
        + f" [yellow]({lines_count} lines)[/yellow]"
    )


class ToolHandler:
    """Handler for processing tool calls"""

    def __init__(
        self,
        tool_registry: "ToolRegistry",
        result_manager: "ResultManager",
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

        all_func_names: list[str] = []
        all_func_kwargs: list[dict[str, str]] = []
        results: list[str] = []

        for func_name, func_kwargs in parsed_input.funcs:
            all_func_names.append(func_name)
            all_func_kwargs.append(func_kwargs)

            parms: str = f"{{{func_kwargs}"

            # 避免多参数工具的返回值过于占上下文
            if len(parms) > 120:
                parms = parms[:117] + "..."

            parms += "}"

            # 执行
            try:
                response = self.tool_registry.execute(func_name, **func_kwargs)
                if isinstance(response, str):
                    response_str = response
                elif isinstance(response, (dict, list, tuple)):
                    response_str = json.dumps(response)
                else:
                    response_str = f"<not_support_result>{response.__class__.__name__}({response})</not_support_result>"

                temp_result = [
                    "",
                    f"<func_result name={func_name} parms={parms}>",
                    response_str,
                    "</func_result>",
                    "",
                ]
                results.append(str.join("\n", temp_result))
            except Exception as e:
                import traceback

                error = (
                    f"执行工具{func_name}(参数={parms})时出现错误: "
                    f"Error={e.__class__.__name__}({e}, {traceback.format_exc()})"
                )
                self.console.print(f"[red]{error}[/red]")
                summary = "\n".join(["", "<ErrorExecute>", error, "/<ErrorExecute>", ""])
                results.append(summary)
                self.console.print(f"[red]{error}[/red]")
                continue

        result = str.join("\n", results)

        if len(all_func_names) == 1:
            # Add to result manager
            entry = self.result_manager.add(all_func_names[0], result)
            # Format and display result
            self._display_result(entry, all_func_names[0], all_func_kwargs[0], result)
        elif len(all_func_names) > 1:
            names = str.join(", ", all_func_names)
            entry = self.result_manager.add(names, result)
            self._display_result(entry, names, {}, result)

        if len(all_func_names) >= 1:
            _auto_view_if_enabled()

        return True

    def _display_result(
        self,
        entry,
        func_name: str,
        func_kwargs: dict,
        result: Any,
    ) -> None:
        """Display tool execution result"""
        result_str = str(result)
        lines_count = result_str.count("\n") + 1

        # Create title
        title = _create_result_title(entry.index, func_name, func_kwargs, lines_count)

        # Detect language
        language = _detect_language(func_name, func_kwargs)

        # Add to viewer
        add_to_viewer(str(entry.index), title, result_str, language)

        # Show brief message
        self.console.print(f"[dim]✓ Result ##{entry.index} added to viewer.[/dim]")
