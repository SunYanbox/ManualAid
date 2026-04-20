"""Command handler for dispatching and executing commands"""

from typing import TYPE_CHECKING

from rich.console import Console

from src.console.commands.base import CommandContext
from src.console.commands.registry import CommandRegistry

if TYPE_CHECKING:
    from src.console.result_manager import ResultManager
    from src.core.tool_registry import ToolRegistry
    from src.workspace.workspace import Workspace


class CommandHandler:
    """Handler for processing console commands"""

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
        self.registry = CommandRegistry.create_default()

    def handle(self, parsed_input) -> bool:
        """Handle a parsed command input

        Args:
            parsed_input: CommandResult from input_parser

        Returns:
            True if handled successfully, False otherwise
        """
        if not parsed_input.is_command:
            return False

        context = CommandContext(
            workspace=self.workspace,
            tool_registry=self.tool_registry,
            result_manager=self.result_manager,
            console=self.console,
            parsed_input=parsed_input,
        )

        result = self.registry.execute(parsed_input.command_type, context)

        if not result.success and result.message:
            self.console.print(f"[red]Error: {result.message}[/red]")

        return result.success
