"""REPL loop implementation"""

from typing import TYPE_CHECKING

from rich.console import Console, Group
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text

from src.console.commands.base import Command, CommandContext, CommandResult
from src.console.commands.registry import CommandRegistry
from src.console.handlers.command_handler import CommandHandler
from src.console.handlers.tool_handler import ToolHandler
from src.console.input_parser import parse_input

if TYPE_CHECKING:
    from src.console.result_manager import ResultManager
    from src.core.tool_registry import ToolRegistry
    from src.workspace.workspace import Workspace


def generate_help(cmds: list[Command]) -> Panel:
    table: Table = Table(show_header=True, title="Available Commands", header_style="bold magenta")
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Aliases", style="cyan", no_wrap=True)
    table.add_column("Description", style="cyan", no_wrap=True)
    table.add_column("Usage", style="cyan", no_wrap=True)
    for cmd in cmds:
        alias_list = [f"[italic magenta]{a.strip()}[/]" for a in cmd.aliases]
        table.add_row(
            cmd.name, " | ".join(alias_list), f"[grey85]{cmd.description}[/grey85]", f"[green]{cmd.usage}[/green]"
        )
    tools_hint = Text()
    tools_hint.append("\n")
    tools_hint.append("Tools: \n", style="bold cyan")
    tools_hint.append("Use Tools with XML tags like: \n", style="dim")
    tools_hint.append(
        '<func_call>{"func_name": "tool_name", "args": [...], "kwargs": {...}}</func_call>\n', style="yellow bold"
    )

    renderable = Group(table, tools_hint)

    panel = Panel(renderable, title="Help", border_style="white")
    return panel


class HelpCommand(Command):
    """Show help message"""

    def __init__(self, cmd_registry: CommandRegistry):
        super().__init__()
        self.name = "help"
        self.aliases = ["/help", "/h", "/?"]
        self.description = "Show help message"
        self.usage = "/help or /h or /?"
        self.cmd_registry = cmd_registry

    def execute(self, context: CommandContext) -> CommandResult:
        context.console.print(generate_help(self.cmd_registry.list_commands()))
        return CommandResult(success=True)


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
        self.command_handler.registry.register(HelpCommand(self.command_handler.registry))
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
        self.console.print(generate_help(self.command_handler.registry.list_commands()))
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
