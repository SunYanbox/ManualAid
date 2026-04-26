from dataclasses import field

from src.models.commands.command_context import CommandContext
from src.models.commands.command_result import CommandResult


class Command:
    """Base class for all commands"""

    name: str = ""
    aliases: list[str] = field(default_factory=list)
    description: str = ""
    usage: str = ""

    def can_handle(self, command_type: str) -> bool:
        """Check if this command can handle the given command type"""
        return command_type == self.name or command_type in self.aliases

    def execute(self, context: CommandContext) -> CommandResult:
        """Execute the command"""
        raise NotImplementedError("Subclasses must implement execute()")
