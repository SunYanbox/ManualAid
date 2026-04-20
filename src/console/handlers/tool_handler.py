"""Tool handler for executing tool calls"""

import json
import os
import re
from typing import TYPE_CHECKING, Any

from rich.console import Console

from src.console.interactive_viewer import add_to_viewer, run_viewer
from src.constants.files import EXTENSION_TO_LANGUAGE
from src.core.parse_func_call import parse_func_call

if TYPE_CHECKING:
    from src.console.result_manager import ResultManager
    from src.core.tool_registry import ToolRegistry


def _auto_view_if_enabled() -> None:
    """Auto-run viewer if enabled"""
    auto_view = os.getenv("MANUALAID_AUTO_VIEW", "").lower() in ("true", "1", "yes", "on")
    if auto_view:
        run_viewer()


def _detect_language(func_name: str, func_args: list, func_kwargs: dict) -> str | None:
    """Detect language for syntax highlighting"""
    if func_name != "read_file":
        return None

    file_path = ""
    if func_args and isinstance(func_args[0], str):
        file_path = func_args[0]
    elif "file_path" in func_kwargs:
        file_path = func_kwargs["file_path"]

    ext_map = EXTENSION_TO_LANGUAGE

    for ext, lang in ext_map.items():
        if file_path.lower().endswith(ext):
            return lang

    return "text"


def _format_tool_params(args: list, kwargs: dict) -> str:
    """Format tool parameters as concise string"""
    parts = []

    # Positional arguments
    for arg in args:
        if isinstance(arg, str):
            arg_str = arg if len(arg) <= 30 else f"{arg[:27]}..."
            parts.append(f'"{arg_str}"')
        else:
            parts.append(str(arg))

    # Keyword arguments
    for key, value in kwargs.items():
        if isinstance(value, str):
            val_str = value if len(value) <= 30 else f"{value[:27]}..."
            parts.append(f'{key}="{val_str}"')
        else:
            parts.append(f"{key}={value}")

    if not parts:
        return "no parameters"

    params_str = ", ".join(parts)
    if len(params_str) > 50:
        params_str = params_str[:47] + "..."

    return params_str


def _create_result_title(index: int, func_name: str, args: list, kwargs: dict, lines_count: int) -> str:
    """Create result title with Rich markup"""
    params_str = _format_tool_params(args, kwargs)
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
        console: Console,
    ):
        self.tool_registry = tool_registry
        self.result_manager = result_manager
        self.console = console

    def handle(self, parsed_input) -> bool:
        """Handle a parsed tool call input

        Args:
            parsed_input: CommandResult from input_parser

        Returns:
            True if handled successfully, False otherwise
        """
        if parsed_input.is_command:
            return False

        user_input = parsed_input.raw_input

        pattern = r"(<func_call>.*?</func_call>)"
        matches = re.findall(pattern, user_input, re.DOTALL)

        all_func_names: list[str] = []
        all_func_args: list[list] = []
        all_func_kwargs: list[dict[str, str]] = []
        results: list[str] = []

        for m in matches:
            # 解析
            try:
                func_name, func_args, func_kwargs = parse_func_call(m)
                all_func_names.append(func_name)
                all_func_args.append(func_args)
                all_func_kwargs.append(func_kwargs)
            except json.JSONDecodeError as json_err:
                self.console.print(f"[yellow] Json decode error: {json_err}[/yellow]")
                continue
            except Exception as e:
                self.console.print(f"[red]Parse error: {e}[/red]")
                return False
            # 执行
            try:
                response = self.tool_registry.execute(func_name, *func_args, **func_kwargs)
                if isinstance(response, str):
                    response_str = response
                elif isinstance(response, (dict, list, tuple)):
                    response_str = json.dumps(response)
                else:
                    response_str = f"<not_support_result>{response.__class__.__name__}({response})</not_support_result>"

                temp_result = [
                    "",
                    f"<func_result name={func_name} args={func_args} kwargs={func_kwargs}>",
                    response_str,
                    "</func_result>",
                    "",
                ]
                results.append(str.join("\n", temp_result))
            except Exception as e:
                self.console.print(f"[red]Execution error: {e}[/red]")
                return False

        result = str.join("\n", results)

        if len(all_func_names) == 1:
            # Add to result manager
            entry = self.result_manager.add(all_func_names[0], result)
            # Format and display result
            self._display_result(entry, all_func_names[0], all_func_args[0], all_func_kwargs[0], result)
        elif len(all_func_names) > 1:
            names = str.join(", ", all_func_names)
            entry = self.result_manager.add(names, result)
            self._display_result(entry, names, [], {}, result)

        if len(all_func_names) >= 1:
            _auto_view_if_enabled()

        return True

    def _display_result(
        self,
        entry,
        func_name: str,
        func_args: list,
        func_kwargs: dict,
        result: Any,
    ) -> None:
        """Display tool execution result"""
        result_str = str(result)
        lines_count = result_str.count("\n") + 1

        # Create title
        title = _create_result_title(entry.index, func_name, func_args, func_kwargs, lines_count)

        # Detect language
        language = _detect_language(func_name, func_args, func_kwargs)

        # Add to viewer
        add_to_viewer(str(entry.index), title, result_str, language)

        # Show brief message
        self.console.print(f"[dim]✓ Result ##{entry.index} added to viewer.[/dim]")

        # Auto-copy notification
        if self.result_manager.AUTO_COPY and not func_name.startswith(("tool_prompt", "workspace_prompt")):
            self.console.print("[dim](Auto-copied to clipboard)[/dim]")
