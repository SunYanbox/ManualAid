"""Workspace-related commands (prompt, workspace)"""

from src.console.commands.base import Command, CommandContext, CommandResult
from src.console.interactive_viewer import add_to_viewer

INSTRUCTION: list[str] = ["AGENTS.md", "CLAUDE.md"]


def _generate_tool_prompt(context: CommandContext) -> str:
    """Generate LLM prompt for available tools"""
    tools = context.tool_registry.list_tools()
    if not tools.get("sync"):
        return "No tools available."

    prompt_parts = [
        "## TOOL USAGE RULES (STRICT)",
        "1. When you need external data/action, you MUST call a tool using the format below.",
        "2. You MAY call multiple tools in one response. Place each <func_call> block on a NEW LINE.",
        "3. After outputting tool call(s), STOP and WAIT for user to provide results.",
        "4. NEVER hallucinate tool return values. NEVER proceed without actual results.",
        "5. If a tool call fails or returns empty, ask the user for clarification.",
        "",
        "## JSON FORMATTING & ESCAPING (CRITICAL)",
        "The content inside <func_call> MUST be valid JSON.",
        '- Double quotes inside strings MUST be escaped with backslash: \\"',
        "- Backslashes MUST be escaped: \\\\",
        "- Newlines MUST be escaped: \\n",
        "- Example: {'old_str': 'He said \\\"hi\\\"'} is CORRECT.",
        "- Example: {'old_str': 'He said \"hi\"'} is WRONG and will fail.",
        "",
        "Tool call format:",
        "```txt",
        '<func_call>{"func_name": "tool_name", "args": [...], "kwargs": {...}}</func_call>',
        "```",
        "",
        "Multiple tool calls example (NOTE the newlines):",
        "```txt",
        '<func_call>{"func_name": "search", "kwargs": {"q": "weather"}}</func_call>',
        '<func_call>{"func_name": "translate", "kwargs": {"text": "result", "to": "zh"}}</func_call>',
        "```",
        "",
        "Available tools:",
        "",
    ]

    for name in tools["sync"]:
        info = context.tool_registry.get_tool_info(name)
        if info:
            prompt_parts.append(info.to_markdown())

    return "\n".join(prompt_parts)


def _generate_workspace_prompt(context: CommandContext) -> str:
    """Generate workspace metadata prompt"""
    workspace = context.workspace
    root = str(workspace.root_path)
    is_git = workspace.is_git_repo
    platform = workspace.platform

    prompt: str = ""

    for agent_instruction in INSTRUCTION:
        agents_md = workspace.root_path / agent_instruction

        if agents_md.exists():
            with open(agents_md, encoding="utf-8") as f:
                prompt += f.read() + "\n"
            break

    prompt += (
        "\n# SYSTEM CONSTRAINTS\n"
        "- You are a semi-automated assistant. You DO NOT have direct access to the file system or web.\n"
        "- You MUST rely on tools provided by the user.\n"
        "- AFTER emitting all <func_call> block you need, you MUST STOP generating text immediately.\n"
        "- Do NOT say 'Here is the result' or simulate the result. WAIT for the user to paste the output.\n"
    )

    # 仓库元数据
    prompt += (
        f'# Workspace Metadata\n\n<workspace root="{root}" git="{is_git}" +\n'
        f'    platform="{platform}" date="{workspace.date}" />'
    )

    return prompt


class PromptCommand(Command):
    """Generate LLM tool call prompt"""

    def __init__(self):
        super().__init__()
        self.name = "prompt"
        self.aliases = ["/prompt", "/pmt"]
        self.description = "Generate tool call prompt"
        self.usage = "/prompt or /pmt"

    def execute(self, context: CommandContext) -> CommandResult:
        prompt = _generate_tool_prompt(context)
        entry = context.result_manager.add("tool_prompt", prompt)

        lines_count = prompt.count("\n") + 1
        title = (
            f"[bold cyan]##{entry.index}[/bold cyan] [bold green]tool_prompt[/bold green] "
            + f"[yellow]({lines_count} lines)[/yellow]"
        )

        add_to_viewer(str(entry.index), title, prompt, "markdown")
        context.console.print(f"[dim]✓ Tool prompt ##{entry.index} added to viewer.[/dim]")
        return CommandResult(success=True)


class WorkspaceCommand(Command):
    """Generate workspace metadata prompt"""

    def __init__(self):
        super().__init__()
        self.name = "workspace"
        self.aliases = ["/workspace", "/ws"]
        self.description = "Generate workspace metadata prompt"
        self.usage = "/workspace or /ws"

    def execute(self, context: CommandContext) -> CommandResult:
        prompt = _generate_workspace_prompt(context)
        entry = context.result_manager.add("workspace_prompt", prompt)

        lines_count = prompt.count("\n") + 1
        title = (
            f"[bold cyan]##{entry.index}[/bold cyan] [bold green]workspace_prompt[/bold green]"
            + f" [yellow]({lines_count} lines)[/yellow]"
        )

        add_to_viewer(str(entry.index), title, prompt)
        context.console.print(f"[dim]✓ Workspace prompt ##{entry.index} added to viewer.[/dim]")
        return CommandResult(success=True)
