"""System-related commands (help, quit, tools)"""

import os
import platform
import sys

from rich.panel import Panel
from rich.table import Table

from src.console.commands.base import Command, CommandContext, CommandResult


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
        return CommandResult(success=True)


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
                table.add_row(name, info.to_markdown())

        context.console.print(table)
        return CommandResult(success=True)


class ToolDetailCommand(Command):
    """Show details of a specific tool"""

    def __init__(self):
        super().__init__()
        self.name = "tool_detail"
        self.aliases = ["/tool"]
        self.description = "Show details of a specific tool"
        self.usage = "/tool <name>"

    def execute(self, context: CommandContext) -> CommandResult:
        parts = context.parsed_input.source.split()
        if len(parts) >= 2:
            name = parts[1]
        else:
            return CommandResult(success=False, message=f"Input cmd cant parse func name: '{context.parsed_input}'")

        if not name:
            return CommandResult(success=False, message="Tool name required")

        info = context.tool_registry.get_tool_info(name)
        if not info:
            context.console.print(f"[red]Tool '{name}' not found.[/red]")
            return CommandResult(success=False, message=f"Tool '{name}' not found")

        details = f"""[bold]Tool:[/bold] {info.name}

[bold]Doc:[/bold] {info.doc}

[bold]Params:[/bold]
"""
        for param, param_info in info.params.items():
            required = "required" if param_info.get("required") else "optional"
            default = f" (default: {param_info.get('default')})" if "default" in param_info else ""
            details += f"  - {param}: {param_info.get('annotation')} [{required}]{default}\n"

        context.console.print(Panel(details, title=f"Tool: {name}"))
        return CommandResult(success=True)
