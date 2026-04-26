"""System-related commands (help, quit, tools)"""

import os
import platform
import sys

from rich.panel import Panel
from rich.table import Table

from src.models.commands import Command, CommandContext, CommandResult


def generate_help_text(cmds: list[Command]) -> str:
    """生成帮助文本,返回 Rich markup 字符串"""
    lines: list[str] = [
        "[bold magenta]可用命令[/bold magenta]\n",
        "  [cyan]名称[/cyan]          [cyan]别名[/cyan]              [cyan]描述[/cyan]",
        "  " + chr(9472) * 70,
    ]
    for cmd in cmds:
        alias_str = " | ".join(f"[italic magenta]{a}[/italic magenta]" for a in cmd.aliases)
        lines.append(f"  [cyan]{cmd.name:<16}[/cyan] {alias_str:<24} [grey85]{cmd.description}[/grey85]")
    lines.append("")
    lines.append("[bold cyan]工具:[/bold cyan]")
    lines.append("[dim]使用 XML 标签调用工具,格式如下:[/dim]")
    lines.append(
        """[yellow bold]
<func_call>
    <func_name>工具名称</func_name>
    <param name="参数名称">参数值</param>
</func_call>
        [/yellow bold]
        """
    )
    return "\n".join(lines)


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


class HelpCommand(Command):
    """显示帮助信息"""

    def __init__(self):
        super().__init__()
        self.name = "help"
        self.aliases = ["/help", "/h", "/?"]
        self.description = "显示帮助信息"
        self.usage = "/help 或 /h 或 /?"

    def execute(self, context: CommandContext) -> CommandResult:
        context.console.print(generate_help_text(context.command_registry.list_commands()))
        return CommandResult(success=True)


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
