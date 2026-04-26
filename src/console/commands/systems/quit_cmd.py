import sys

from src.models.commands import Command, CommandContext, CommandResult


class QuitCommand(Command):
    """Exit the console"""

    def __init__(self):
        super().__init__()
        self.name = "quit"
        self.aliases = ["/quit", "/q", "/exit"]
        self.description = "Exit the console"
        self.usage = "/quit or /q or /exit"

    def execute(self, context: CommandContext) -> CommandResult:
        context.console.print("[bold]Goodbye![/bold]")
        sys.exit(0)
