"""Agent management command (/agent)."""

from __future__ import annotations

import pyperclip

from src.core.agent_manager import AgentManager
from src.models.commands import Command, CommandContext, CommandResult


class AgentCommand(Command):
    """Manage Agent configuration"""

    def __init__(self):
        super().__init__()
        self.name = "agent"
        self.aliases = ["/agent"]
        self.description = "Manage agent configuration (list, switch, copy)"
        self.usage = (
            "/agent — show current agent\n"
            "/agent list — list all agents\n"
            "/agent <name> — switch to agent by name or unique prefix\n"
            "/agent default — switch to default agent\n"
            "/agent copy — copy current agent's role+workflow to clipboard\n"
            "/agent copy <name> — copy specified agent's role+workflow to clipboard"
        )

    def execute(self, context: CommandContext) -> CommandResult:
        mgr = AgentManager()
        args = context.parsed_input.args.strip()

        if not args:
            return self._show_current(mgr, context)
        if args == "list":
            return self._list_all(mgr, context)
        if args.startswith("copy"):
            rest = args[4:].strip()
            return self._copy_agent(mgr, context, rest or None)
        if args == "default":
            return self._switch(mgr, "default", context)

        # Treat as agent name (supports unique prefix matching)
        return self._switch(mgr, args, context)

    def _show_current(self, mgr: AgentManager, context: CommandContext) -> CommandResult:
        agent = mgr.get_current()
        context.console.print(
            f"[bold]Current Agent:[/bold] {agent.name}\n"
            f"[dim]{agent.description}[/dim]\n"
            f"Whitelist: {agent.tool_permissions.whitelist or '(all)'}\n"
            f"Blacklist: {agent.tool_permissions.blacklist or '(none)'}"
        )
        return CommandResult(success=True)

    def _list_all(self, mgr: AgentManager, context: CommandContext) -> CommandResult:
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
            context.console.print(
                f"[red]Ambiguous prefix '{name}' matches: {', '.join(matches)}[/red]"
            )
        else:
            context.console.print(f"[red]Agent '{name}' not found.[/red]")
            context.console.print("Use [bold]/agent list[/bold] to see available agents.")
        return CommandResult(success=True)

    def _copy_agent(self, mgr: AgentManager, context: CommandContext, name: str | None) -> CommandResult:
        if name:
            # Resolve name (exact or unique prefix)
            agent = mgr.get(name)
            if agent is None:
                matches = [n for n in mgr.agent_names() if n.startswith(name)]
                if len(matches) == 1:
                    agent = mgr.get(matches[0])
                elif len(matches) > 1:
                    context.console.print(
                        f"[red]Ambiguous prefix '{name}' matches: {', '.join(matches)}[/red]"
                    )
                    return CommandResult(success=False)
                else:
                    context.console.print(f"[red]Agent '{name}' not found.[/red]")
                    return CommandResult(success=False)
        else:
            agent = mgr.get_current()

        text = self._format_agent_copy(agent)
        try:
            pyperclip.copy(text)
            context.console.print(f"[green]Agent '{agent.name}' settings copied to clipboard.[/green]")
        except Exception:
            context.console.print(text)
            context.console.print("[yellow](pyperclip unavailable — printed above instead)[/yellow]")
        return CommandResult(success=True)

    @staticmethod
    def _format_agent_copy(agent: "AgentConfig") -> str:
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
