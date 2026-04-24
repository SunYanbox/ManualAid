"""Command registry for managing and dispatching commands"""

from src.console.commands.base import Command, CommandContext, CommandResult


class CommandRegistry:
    """Registry for console commands"""

    def __init__(self):
        self._commands: list[Command] = []

    def register(self, command: Command) -> None:
        """Register a command"""
        self._commands.append(command)

    def register_many(self, commands: list[Command]) -> None:
        """Register multiple commands"""
        self._commands.extend(commands)

    def find_command(self, command_type: str) -> Command | None:
        """Find a command that can handle the given command type"""
        for command in self._commands:
            if command.can_handle(command_type):
                return command
        return None

    def execute(self, command_type: str, context: CommandContext) -> CommandResult:
        """Find and execute a command"""
        command = self.find_command(command_type)
        if command:
            return command.execute(context)
        return CommandResult(success=False, message=f"Unknown command: {command_type}")

    def list_commands(self) -> list[Command]:
        """List all registered commands with their aliases and descriptions"""
        return self._commands

    @classmethod
    def create_default(cls) -> "CommandRegistry":
        """Create and populate a registry with default commands"""
        from src.console.commands.launch_commands import (
            NewWindowCommand,
        )
        from src.console.commands.result_commands import (
            CopyCommand,
            HistoryCommand,
            ViewClearCommand,
            ViewCommand,
            ViewRemoveCommand,
        )
        from src.console.commands.system_commands import (
            QuitCommand,
            ToolDetailCommand,
            ToolsCommand,
        )
        from src.console.commands.workspace_commands import WorkspaceCommand

        registry = cls()
        registry.register_many(
            [
                QuitCommand(),
                ToolsCommand(),
                ToolDetailCommand(),
                CopyCommand(),
                HistoryCommand(),
                ViewCommand(),
                ViewClearCommand(),
                ViewRemoveCommand(),
                WorkspaceCommand(),
                NewWindowCommand(),
            ]
        )
        return registry
