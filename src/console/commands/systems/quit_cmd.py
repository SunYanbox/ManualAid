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
        # Close session explicitly before exit (atexit handler is a fallback,
        # but explicit is more reliable when sys.exit triggers early shutdown).
        session_id = getattr(context.tool_registry, "_current_session_id", None)
        if session_id is not None and hasattr(context.workspace, "db"):
            context.workspace.db.close_session(session_id)
        context.console.print("[bold]Goodbye![/bold]")
        sys.exit(0)
