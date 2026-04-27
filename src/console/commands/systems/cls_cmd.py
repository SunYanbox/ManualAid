import os
import platform

from src.models.commands import Command, CommandContext, CommandResult
from src.utils.generate_help_text import generate_help_text


class ClsCommand(Command):
    """Cls command"""

    def __init__(self):
        super().__init__()
        self.name = "cls"
        self.aliases = ["/cls"]
        self.description = "Clear the console"
        self.usage = "/cls"

    def execute(self, context: CommandContext) -> CommandResult:
        # Windows
        if platform.system() == "Windows":
            os.system("cls")
        # Linux/macOS
        else:
            os.system("clear")
        context.console.clear()
        if context.app:
            context.app.refresh()
            context.console.print(generate_help_text(context.command_registry.list_commands()))
        return CommandResult(success=True)
