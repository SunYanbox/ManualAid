"""REPL loop implementation"""

from typing import TYPE_CHECKING

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from src.console.handlers.command_handler import CommandHandler
from src.console.handlers.tool_handler import ToolHandler
from src.console.input_parser import parse_input
from src.constants.commands import HELP_MESSAGE

if TYPE_CHECKING:
    from src.console.result_manager import ResultManager
    from src.core.tool_registry import ToolRegistry
    from src.workspace.workspace import Workspace


class REPL:
    """Read-Eval-Print Loop for ManualAid console"""

    CONSOLE_TITLE = "ManualAid"

    def __init__(
        self,
        workspace: "Workspace",
        tool_registry: "ToolRegistry",
        result_manager: "ResultManager",
        console: Console,
    ):
        self.workspace = workspace
        self.tool_registry = tool_registry
        self.result_manager = result_manager
        self.console = console

        self.command_handler = CommandHandler(workspace, tool_registry, result_manager, console)
        self.tool_handler = ToolHandler(tool_registry, result_manager, console)

    def run(self) -> None:
        """Start the REPL loop"""
        self._print_welcome()

        while True:
            user_input = self._read_multiline_input()

            if not user_input.strip():
                continue

            parsed = parse_input(user_input)

            if parsed.is_command:
                self.command_handler.handle(parsed)
            else:
                self.tool_handler.handle(parsed)

    def _print_welcome(self) -> None:
        """Print welcome message"""
        title_text = f"[bold green]{self.CONSOLE_TITLE}[/bold green] - Workspace: {self.workspace.root_path}"
        self.console.print(Panel(title_text, title=self.CONSOLE_TITLE))
        self.console.print(f"[dim]Workspace: {self.workspace.root_path}[/dim]")
        self.console.print(HELP_MESSAGE)
        self.console.print("[dim]Type /help for commands, /quit to exit.[/dim]\n")

    def _read_multiline_input(self) -> str:
        """Read input, support multi-line for func_call"""
        first_line = Prompt.ask(f"[bold blue]{self.CONSOLE_TITLE}>[/bold blue]")

        if not first_line.strip():
            return first_line

        # Check if this is a func_call that needs multi-line input
        if not (first_line.startswith("<func_call>") and first_line.endswith("</func_call>")):
            return first_line

        if first_line.endswith("</func_call>"):
            return first_line

        lines = [first_line]
        while True:
            cont_line = Prompt.ask("[dim]... [/dim]")
            lines.append(cont_line)
            if cont_line.strip().endswith("</func_call>"):
                break

        return "\n".join(lines)
