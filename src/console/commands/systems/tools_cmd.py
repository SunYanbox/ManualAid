from rich.table import Table

from src.models.commands import Command, CommandContext, CommandResult


class ToolsCommand(Command):
    """List all available tools"""

    def __init__(self):
        super().__init__()
        self.name = "tools"
        self.aliases = ["/tools", "/t"]
        self.description = "List all available tools"
        self.usage = "/tools or /t"

    def execute(self, context: CommandContext) -> CommandResult:
        tools = context.tool_registry.list_tools()
        if not tools.get("sync"):
            context.console.print("[dim]No tools registered.[/dim]")
            return CommandResult(success=True)

        table = Table(title="Available Tools")
        table.add_column("Name", style="cyan")
        table.add_column("Doc", style="dim")

        for name in tools["sync"]:
            info = context.tool_registry.get_tool_info(name)
            if info and info.doc:
                table.add_row(name, info.to_doc())

        context.console.print(table)
        return CommandResult(success=True)
