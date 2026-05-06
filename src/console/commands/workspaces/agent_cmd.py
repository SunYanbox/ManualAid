"""Agent management command (/agent)."""

from __future__ import annotations

from argparse import ArgumentParser

from src.core.agent_manager import AgentManager
from src.core.copy2clip import copy_to_clipboard
from src.models.agent import AgentConfig
from src.models.commands import Command, CommandContext, CommandResult


def _reset_default(mgr: AgentManager, context: CommandContext) -> CommandResult:
    if mgr.reset_default():
        context.console.print("[green]default.md 已根据内置Default Agent重写完成[/green]")
    else:
        context.console.print("[red]重置失败: 工作区根路径未初始化[/red]")
    return CommandResult(success=True)


def _show_current(mgr: AgentManager, context: CommandContext) -> CommandResult:
    agent = mgr.get_current()
    context.console.print(
        f"[bold]Current Agent:[/bold] {agent.name}\n"
        f"[dim]{agent.description}[/dim]\n"
        f"Whitelist: {agent.tool_permissions.whitelist or '(all)'}\n"
        f"Blacklist: {agent.tool_permissions.blacklist or '(none)'}"
    )
    return CommandResult(success=True)


def _list_all(mgr: AgentManager, context: CommandContext) -> CommandResult:
    agents = mgr.list_agents()
    if not agents:
        context.console.print("[yellow]No agents found in .ManualAid/agents/[/yellow]")
        return CommandResult(success=True)

    lines = ["[bold]Available Agents:[/bold]"]
    for a in agents:
        marker = ">" if a.name == mgr.current_agent_name else " "
        lines.append(f"  {marker} {a.name} — {a.description}")
    context.console.print("\n".join(lines))
    return CommandResult(success=True)


class AgentCommand(Command):
    """Manage Agent configuration"""

    def __init__(self):
        super().__init__()
        self.name = "agent"
        self.aliases = ["/agent"]
        self.description = "管理 Agent 配置 (列表、切换、复制、重置)"
        self.usage = (
            "/agent — 显示当前 Agent\n"
            "/agent list — 列出所有 Agent\n"
            "/agent <name> — 按名称或唯一前缀切换 Agent\n"
            "/agent default — 切换到默认 Agent\n"
            "/agent copy — 复制当前 Agent 的角色+工作流到剪贴板\n"
            "/agent copy <name> — 复制指定 Agent 的角色+工作流到剪贴板\n"
            "/agent reset — 根据 prompts.py 重写 default.md"
        )
        self.argparse = ArgumentParser("agent")
        self.argparse.add_argument(
            "subcommand",
            nargs="?",
            default=None,
            help="子命令: list, default, copy, reset, 或 Agent 名称",
        )
        for usage in self.usage.split("\n"):
            self.argparse.add_argument(
                "Usage",
                nargs="?",
                default=None,
                help=usage,
            )

    def execute(self, context: CommandContext) -> CommandResult:
        # Show help on -h / --help
        if "-h" in context.parsed_input.source or "--help" in context.parsed_input.source:
            context.console.print(self.argparse.format_help())
            return CommandResult(success=True)

        mgr = AgentManager()
        # Parse args from source: "/agent list" -> "list"
        parts = context.parsed_input.source.split()
        args = " ".join(parts[1:]) if len(parts) > 1 else ""

        if not args:
            return _show_current(mgr, context)
        if args == "list":
            return _list_all(mgr, context)
        if args.startswith("copy"):
            rest = args[4:].strip()
            return self._copy_agent(mgr, context, rest or None)
        if args == "default":
            return self._switch(mgr, "default", context)
        if args == "reset":
            return _reset_default(mgr, context)

        # Treat as agent name (supports unique prefix matching)
        return self._switch(mgr, args, context)

    def _switch(self, mgr: AgentManager, name: str, context: CommandContext) -> CommandResult:
        # Try exact match first
        if mgr.switch_agent(name):
            agent = mgr.get_current()
            context.console.print(f"[green]Switched to agent:[/green] {agent.name}")
            # Update TUI dropdown if available
            self._sync_tui(context, mgr.current_agent_name)
            return CommandResult(success=True)

        # Try unique prefix match
        matches = [n for n in mgr.agent_names() if n.startswith(name)]
        if len(matches) == 1:
            mgr.switch_agent(matches[0])
            context.console.print(f"[green]Switched to agent:[/green] {matches[0]}")
            self._sync_tui(context, mgr.current_agent_name)
            return CommandResult(success=True)

        if len(matches) > 1:
            context.console.print(f"[red]Ambiguous prefix '{name}' matches: {', '.join(matches)}[/red]")
        else:
            context.console.print(f"[red]Agent '{name}' not found.[/red]")
            context.console.print("Use [bold]/agent list[/bold] to see available agents.")
        return CommandResult(success=True)

    def _copy_agent(self, mgr: AgentManager, context: CommandContext, name: str | None) -> CommandResult:
        if name:
            agent = mgr.get(name)
            if agent is None:
                matches = [n for n in mgr.agent_names() if n.startswith(name)]
                if len(matches) == 1:
                    agent = mgr.get(matches[0])
                elif len(matches) > 1:
                    context.console.print(f"[red]Ambiguous prefix '{name}' matches: {', '.join(matches)}[/red]")
                    return CommandResult(success=False)
                else:
                    context.console.print(f"[red]Agent '{name}' not found.[/red]")
                    return CommandResult(success=False)
        else:
            agent = mgr.get_current()

        text = self._format_agent_copy(agent)
        if copy_to_clipboard(text):
            context.console.print(f"[green]Agent '{agent.name}' settings copied to clipboard.[/green]")
        else:
            context.console.print(text)
            context.console.print("[yellow](Clipboard unavailable — printed above instead)[/yellow]")
        return CommandResult(success=True)

    @staticmethod
    def _format_agent_copy(agent: AgentConfig) -> str:
        """Format agent body (role + workflow) for external pasting."""
        parts = [f"--- Agent: {agent.name} ---", ""]
        if agent.body_role:
            parts.append(agent.body_role)
            parts.append("")
        if agent.body_workflow:
            parts.append(agent.body_workflow)
            parts.append("")
        return "\n".join(parts).strip()

    @staticmethod
    def _sync_tui(context: CommandContext, agent_name: str) -> None:
        """Update TUI dropdown and title bar after agent switch."""
        app = context.app
        if app is None:
            return
        try:
            from textual.widgets import Select

            select = app.query_one("#agent-select", Select)
            if select:
                select.value = agent_name
        except Exception:
            pass
