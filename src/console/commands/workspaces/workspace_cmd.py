"""Workspace-related commands (prompt, workspace)"""

from src.console.ui.interactive_viewer import add_to_viewer
from src.constants.prompts import AGENTIC_LOOP_OVERRIDE_CONTRACT, SYSTEM_CONSTRAINTS, TOOL_BASE_PROMPT
from src.models.commands import Command, CommandContext, CommandResult

INSTRUCTION: list[str] = ["AGENTS.md", "CLAUDE.md"]


def _generate_tool_prompt(context: CommandContext) -> str:
    """Generate LLM prompt for available tools"""
    tools = context.tool_registry.list_tools()
    if not tools.get("sync"):
        return "No tools available."

    prompt_parts = [
        TOOL_BASE_PROMPT,
        "Available tools:",
    ]

    docs = []

    for name in tools["sync"]:
        info = context.tool_registry.get_tool_info(name)
        if info:
            docs.append(info.to_doc())

    prompt_parts = [*prompt_parts, "\n\n".join(docs)]

    return "\n".join(prompt_parts)


def _generate_workspace_metadata(context: CommandContext) -> str:
    workspace = context.workspace
    root = str(workspace.root_path)
    is_git = workspace.is_git_repo
    platform = workspace.platform
    return (
        f"<workspace_info>\n"
        f"  <root_path>{root}</root_path>\n"
        f"  <is_git_repo>{is_git}</is_git_repo>\n"
        f"  <platform>{platform}</platform>\n"
        f"  <date>{workspace.date}</date>\n"
        f"</workspace_info>\n\n"
        f"Note: All file paths are relative to <root_path>. "
        f"Use this context when constructing tool calls."
    )


def _load_agents_md(context: CommandContext) -> str:
    """加载AGENTS.md文件"""
    workspace = context.workspace
    for agent_instruction in INSTRUCTION:
        agents_md = workspace.root_path / agent_instruction

        if agents_md.exists():
            with open(agents_md, encoding="utf-8") as f:
                return AGENTIC_LOOP_OVERRIDE_CONTRACT.replace(
                    "{source}", str(agents_md.relative_to(workspace.root_path))
                ).replace("{content}", f.read())
    return ""


class WorkspaceCommand(Command):
    """Generate workspace metadata prompt"""

    def __init__(self):
        super().__init__()
        self.name = "workspace"
        self.aliases = ["/workspace", "/ws"]
        self.description = "Generate workspace metadata and tool prompt"
        self.usage = "/workspace or /ws"

    def execute(self, context: CommandContext) -> CommandResult:
        prompt = (
            SYSTEM_CONSTRAINTS
            + _generate_tool_prompt(context)
            + "\n"
            + _generate_workspace_metadata(context)
            + "\n\n---\n\n"
            + _load_agents_md(context)
            + "\n\n---\n\n"
        )
        entry = context.result_manager.add("workspace_prompt", prompt)

        lines_count = prompt.count("\n") + 1
        title = (
            f"[bold cyan]##{entry.index}[/bold cyan] [bold green]workspace_prompt[/bold green]"
            + f" [yellow]({lines_count} lines)[/yellow]"
        )

        add_to_viewer(str(entry.index), title, prompt)
        context.console.print(f"[dim]✓ Workspace prompt ##{entry.index} added to viewer.[/dim]")
        return CommandResult(success=True)
