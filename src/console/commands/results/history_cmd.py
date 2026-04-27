from src.models.commands import Command, CommandContext, CommandResult


class HistoryCommand(Command):
    """Show command history"""

    def __init__(self):
        super().__init__()
        self.name = "history"
        self.aliases = ["/history"]
        self.description = "Show command history"
        self.usage = "/history"

    def execute(self, context: CommandContext) -> CommandResult:
        history = context.result_manager.list_history()
        if not history:
            context.console.print("[dim]No history yet.[/dim]")
            return CommandResult(success=True)

        for entry in history:
            copied_mark = " [copied]" if entry.copied else ""
            context.console.print(f"[bold cyan]{entry.index}:[/bold cyan] [bold]{entry.func_name}[/bold]{copied_mark}")
        return CommandResult(success=True)
