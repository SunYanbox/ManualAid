"""Workspace-related commands (prompt, workspace)"""

import warnings

from src.console.ui.interactive_viewer import add_to_viewer
from src.constants.prompts import (
    AUGMENTATION_WRAPPER,
    SYSTEM_IDENTITY,
    TOOL_RULES,
    WORKFLOW_GUIDELINES,
    generate_extensions_section,
)
from src.models.commands import Command, CommandContext, CommandResult

INSTRUCTION: list[str] = ["AGENTS.md", "CLAUDE.md"]
AGENTS_MD_FENCE_START = "<!-- llm-relevant-start -->"
AGENTS_MD_FENCE_END = "<!-- llm-relevant-end -->"


def _generate_tool_definitions_section(context: CommandContext) -> str:
    """Generate <tool_definitions> XML block with doc for each registered tool."""
    tools = context.tool_registry.list_tools()
    if not tools.get("sync"):
        return "<tool_definitions><!-- 没有可用的工具 --></tool_definitions>"

    docs: list[str] = ["<tool_definitions>"]
    for name in tools["sync"]:
        info = context.tool_registry.get_tool_info(name)
        if info:
            doc_xml = info.to_doc()
            if doc_xml:
                docs.append(f"  {doc_xml}")
    docs.append("</tool_definitions>")
    return "\n".join(docs)


def _generate_workspace_metadata(context: CommandContext) -> str:
    """Generate <workspace_context> XML block with project metadata."""
    workspace = context.workspace
    root = str(workspace.root_path)
    is_git = workspace.is_git_repo
    platform = workspace.platform
    return (
        f"<workspace_context>\n"
        f"  <root_path>{root}</root_path>\n"
        f"  <is_git_repo>{is_git}</is_git_repo>\n"
        f"  <platform>{platform}</platform>\n"
        f"  <date>{workspace.date}</date>\n"
        f"</workspace_context>\n\n"
        f"Note: All file paths are relative to <root_path>. "
        f"Use this context when constructing tool calls."
    )


def _load_agents_md(context: CommandContext) -> str:
    """Load AGENTS.md and extract LLM-relevant sections (between fence markers)."""
    workspace = context.workspace
    for agent_instruction in INSTRUCTION:
        agents_md = workspace.root_path / agent_instruction

        if agents_md.exists():
            with open(agents_md, encoding="utf-8") as f:
                content = f.read()

            start_idx = content.find(AGENTS_MD_FENCE_START)
            end_idx = content.find(AGENTS_MD_FENCE_END)

            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                relevant = content[start_idx + len(AGENTS_MD_FENCE_START) : end_idx].strip()
            else:
                relevant = content.strip()
                warnings.warn(
                    f"{agents_md.relative_to(workspace.root_path)} is missing LLM-relevant fence markers. "
                    f"Add {AGENTS_MD_FENCE_START}/{AGENTS_MD_FENCE_END} to filter content. "
                    f"Injecting full content as fallback.",
                    UserWarning,
                    stacklevel=2,
                )

            return AUGMENTATION_WRAPPER.replace("{source}", str(agents_md.relative_to(workspace.root_path))).replace(
                "{content}", relevant
            )
    return ""


def _assemble_full_prompt(context: CommandContext) -> str:
    """Assemble the complete system prompt from ordered XML sections."""
    sections = [
        "<system_prompt>",
        "",
        SYSTEM_IDENTITY,
        "",
        TOOL_RULES,
        "",
        _generate_tool_definitions_section(context),
        "",
        WORKFLOW_GUIDELINES,
        "",
        _generate_workspace_metadata(context),
        "",
    ]

    augmentations = _load_agents_md(context)
    if augmentations:
        sections.append(augmentations)
        sections.append("")

    sections.append(generate_extensions_section())
    sections.append("")
    sections.append("</system_prompt>")

    return "\n".join(sections)


class WorkspaceCommand(Command):
    """Generate workspace metadata prompt"""

    def __init__(self):
        super().__init__()
        self.name = "workspace"
        self.aliases = ["/workspace", "/ws"]
        self.description = "Generate workspace metadata and tool prompt"
        self.usage = "/workspace or /ws"

    def execute(self, context: CommandContext) -> CommandResult:
        prompt = _assemble_full_prompt(context)
        entry = context.result_manager.add("workspace_prompt", prompt)

        lines_count = prompt.count("\n") + 1
        title = (
            f"[bold cyan]##{entry.index}[/bold cyan] [bold green]workspace_prompt[/bold green]"
            + f" [yellow]({lines_count} lines)[/yellow]"
        )

        add_to_viewer(str(entry.index), title, prompt)
        context.console.print(f"[dim]✓ Workspace prompt ##{entry.index} added to viewer.[/dim]")
        return CommandResult(success=True)
