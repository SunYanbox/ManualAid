"""Workspace-related commands (prompt, workspace)"""

import warnings

from src.constants.prompts import (
    AUGMENTATION_WRAPPER,
    SYSTEM_CONSTRAINTS,
    SYSTEM_ROLE,
    TOOL_RULES,
    WORKFLOW_GUIDELINES,
    generate_extensions_section,
)
from src.core.agent_manager import AgentManager
from src.models.agent import AgentConfig
from src.models.commands import Command, CommandContext, CommandResult

INSTRUCTION: list[str] = ["AGENTS.md", "CLAUDE.md"]
AGENTS_MD_FENCE_START = "<!-- llm-relevant-start -->"
AGENTS_MD_FENCE_END = "<!-- llm-relevant-end -->"


def _generate_tool_definitions_section(context: CommandContext, agent: AgentConfig) -> str:
    """Generate <tool_definitions> XML block with doc for each registered tool,
    filtered by the current agent's tool permissions."""
    tools = context.tool_registry.list_tools()

    if not tools.get("sync"):
        return "<tool_definitions><!-- 没有可用的工具 --></tool_definitions>"

    docs: list[str] = ["<tool_definitions>"]
    for name in tools["sync"]:
        # Filter by agent permissions
        if not agent.tool_permissions.is_tool_allowed(name):
            continue
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


def _generate_agent_directive_section(agent: AgentConfig) -> str:
    """Generate <agent_directive> XML block from the current agent."""
    if not agent.body_role and not agent.body_workflow:
        return ""

    parts = [f'  <agent_directive name="{agent.name}" precedence="OVERRIDES_BASE">', ""]
    if agent.body_role:
        parts.append(agent.body_role)
        parts.append("")
    if agent.body_workflow:
        parts.append(agent.body_workflow)
        parts.append("")
    parts.append("  </agent_directive>")
    return "\n".join(parts)


def _assemble_full_prompt(context: CommandContext) -> str:
    """Assemble the complete system prompt from ordered XML sections.

    Order: role → constraints → agent_directive → tool_rules → tool_definitions
           → workflow → workspace_context → augmentation → extensions
    """
    agent = AgentManager().get_current()

    sections = [
        "<system_prompt>",
        "",
    ]

    # ① System role — skip if agent provides its own role
    if not agent.body_role:
        sections.append(SYSTEM_ROLE)
        sections.append("")

    # ② System constraints — always injected (anti-hallucination handled by tool_rules)
    sections.append(SYSTEM_CONSTRAINTS)
    sections.append("")

    # ③ Agent directive (role + workflow from agent .md file, if any)
    agent_directive = _generate_agent_directive_section(agent)
    if agent_directive:
        sections.append(agent_directive)
        sections.append("")

    # ④ Tool call format rules
    sections.append(TOOL_RULES)
    sections.append("")

    # ⑤ Tool definitions
    sections.append(_generate_tool_definitions_section(context, agent))
    sections.append("")

    # ⑥ Workflow guidelines — skip if agent provides its own workflow
    if not agent.body_workflow:
        sections.append(WORKFLOW_GUIDELINES)
        sections.append("")

    # ⑦ Workspace metadata
    sections.append(_generate_workspace_metadata(context))
    sections.append("")

    # ⑧ Augmentations from AGENTS.md / CLAUDE.md
    augmentations = _load_agents_md(context)
    if augmentations:
        sections.append(augmentations)
        sections.append("")

    # ⑨ Extensions (Skills / MCP hooks)
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
        context.result_manager.add("workspace_prompt", prompt)
        return CommandResult(success=True)
