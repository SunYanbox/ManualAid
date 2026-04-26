"""Result-related commands (copy, history, view)"""

from src.console.ui.interactive_viewer import (
    clear_viewer,
    get_viewer,
    run_viewer,
)
from src.models.commands import Command, CommandContext, CommandResult


class CopyCommand(Command):
    """Copy result to clipboard"""

    def __init__(self):
        super().__init__()
        self.name = "copy"
        self.aliases = ["/copy", "/c"]
        self.description = "Copy result to clipboard"
        self.usage = "/copy <n> or /c <n>"

    def execute(self, context: CommandContext) -> CommandResult:
        index = context.parsed_input.cmd_kwargs.get("index")

        if index is None:
            history = context.result_manager.list_history()
            if not history:
                context.console.print("[yellow]No history to copy.[/yellow]")
                return CommandResult(success=False, message="No history")
            index = history[-1].index

        if context.result_manager.copy_to_clipboard(index):
            context.console.print(f"[green]Result #{index} copied to clipboard.[/green]")
            return CommandResult(success=True)
        else:
            context.console.print(f"[red]Failed to copy result #{index}.[/red]")
            return CommandResult(success=False, message="Copy failed")


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


class ViewCommand(Command):
    """Open interactive result viewer"""

    def __init__(self):
        super().__init__()
        self.name = "view"
        self.aliases = ["/view", "/v"]
        self.description = "Open interactive result viewer"
        self.usage = "/view or /v"

    def execute(self, context: CommandContext) -> CommandResult:
        run_viewer()
        return CommandResult(success=True)


class ViewClearCommand(Command):
    """Clear all items from viewer"""

    def __init__(self):
        super().__init__()
        self.name = "view_clear"
        self.aliases = ["/view_clear"]
        self.description = "Clear all items from viewer"
        self.usage = "/view_clear"

    def execute(self, context: CommandContext) -> CommandResult:
        clear_viewer()
        context.console.print("[green]Viewer cleared.[/green]")
        return CommandResult(success=True)


class ViewRemoveCommand(Command):
    """Remove specific item from viewer"""

    def __init__(self):
        super().__init__()
        self.name = "view_remove"
        self.aliases = ["/view_remove"]
        self.description = "Remove item from viewer"
        self.usage = "/view_remove <n>"

    def execute(self, context: CommandContext) -> CommandResult:
        index = context.parsed_input.cmd_kwargs.get("index")
        if index:
            viewer = get_viewer()
            if viewer.remove_item(str(index)):
                context.console.print(f"[green]Item #{index} removed from viewer.[/green]")
                return CommandResult(success=True)
            else:
                context.console.print(f"[yellow]Item #{index} not found in viewer.[/yellow]")
                return CommandResult(success=False, message="Item not found")
        return CommandResult(success=False, message="Index required")
