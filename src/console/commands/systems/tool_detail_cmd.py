from rich.panel import Panel

from src.models.commands import Command, CommandContext, CommandResult


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
