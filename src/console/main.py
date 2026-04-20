import os
import sys
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from src.console.folder_picker import pick_folder
from src.console.input_parser import parse_input
from src.console.interactive_viewer import add_to_viewer, clear_viewer, get_viewer, run_viewer
from src.console.result_manager import ResultManager
from src.core.parse_func_call import parse_func_call
from src.core.tool_registry import ToolRegistry
from src.workspace.workspace import Workspace

console = Console()
result_manager = ResultManager()
tool_registry = ToolRegistry()
CONSOLE_TITLE = "ManualAid"
HELP_MESSAGE = """[bold]Available Commands:[/bold]
  /copy <n>  or /c <n>  - Copy result #n to clipboard (no <n> copies last)
  /history               - Show command history
  /help       or /h      - Show this help message
  /tools       or /t     - List available tools
  /tool <name>           - Show tool details
  /prompt                - Generate LLM tool call prompt
  /workspace   or /ws    - Generate workspace metadata prompt
  /view       or /v      - Open interactive result viewer
  /view_clear            - Clear all items from viewer
  /view_remove <n>       - Remove item #n from viewer
  /quit       or /q      - Exit console
  <func_call>...         - Execute tool call

[bold]Viewer Controls:[/bold]
  ↑/↓: Navigate items
  Enter/Space: Expand/Collapse
  Delete: Remove current item
  Home/End: Jump to first/last
  q/Esc: Exit viewer"""


def init_workspace() -> Workspace | None:
    """Initialize workspace"""
    folder_path = pick_folder()
    if not folder_path:
        console.print("[bold red]No folder selected. Exiting.[/bold red]")
        sys.exit(0)
    console.print(f"[green]Workspace:[/green] {folder_path}")
    workspace: Workspace = Workspace(folder_path)

    tool_registry.register_function(workspace.glob)
    tool_registry.register_function(workspace.ls)
    tool_registry.register_function(workspace.read_file)

    return workspace


def execute_tool_call(user_input: str) -> tuple[str, list, dict, Any]:
    """Execute tool call"""
    try:
        func_name, func_args, func_kwargs = parse_func_call(user_input)
    except Exception as e:
        return "", [], {}, f"Parse error: {e}"

    try:
        result = tool_registry.execute(func_name, *func_args, **func_kwargs)
        return func_name, func_args, func_kwargs, result
    except Exception as e:
        return func_name, func_args, func_kwargs, f"Execution error: {e}"


def list_tools() -> None:
    """List all tools"""
    tools = tool_registry.list_tools()
    if not tools.get("sync"):
        console.print("[dim]No tools registered.[/dim]")
        return

    table = Table(title="Available Tools")
    table.add_column("Name", style="cyan")
    table.add_column("Doc", style="dim")

    for name in tools["sync"]:
        info = tool_registry.get_tool_info(name)
        if info and info.doc:
            table.add_row(name, info.to_markdown())

    console.print(table)


def show_tool_details(name: str) -> None:
    """Show tool details"""
    info = tool_registry.get_tool_info(name)
    if not info:
        console.print(f"[red]Tool '{name}' not found.[/red]")
        return

    details = f"""[bold]Tool:[/bold] {info.name}

[bold]Doc:[/bold] {info.doc}

[bold]Params:[/bold]
"""
    for param, param_info in info.params.items():
        required = "required" if param_info.get("required") else "optional"
        default = f" (default: {param_info.get('default')})" if "default" in param_info else ""
        details += f"  - {param}: {param_info.get('annotation')} [{required}]{default}\n"

    console.print(Panel(details, title=f"Tool: {name}"))


def generate_tool_prompt() -> str:
    """Generate LLM prompt for available tools"""
    tools = tool_registry.list_tools()
    if not tools.get("sync"):
        return "No tools available."

    prompt_parts = [
        "You can use the following tools to help with tasks. ",
        "When you need to call a tool, output in this format:",
        "",
        "```txt",
        '<func_call>{"func_name": "tool_name", "args": [arg1, arg2], "kwargs": {"key1": "value1"}}</func_call>',
        "```",
        "",
        "Available tools:",
        "",
    ]

    for name in tools["sync"]:
        info = tool_registry.get_tool_info(name)
        if info:
            prompt_parts.append(info.to_markdown())

    return "\n".join(prompt_parts)


def generate_workspace_prompt(workspace: Workspace) -> str:
    """Generate workspace metadata prompt"""
    root = str(workspace.root_path)
    is_git = workspace.is_git_repo
    platform = workspace.platform

    return f"""<workspace root="{root}" git="{is_git}" platform="{platform}" date="{workspace.date}" />"""


def show_history() -> None:
    """Show command history"""
    history = result_manager.list_history()
    if not history:
        console.print("[dim]No history yet.[/dim]")
        return

    for entry in history:
        copied_mark = " [copied]" if entry.copied else ""
        console.print(f"[bold cyan]{entry.index}:[/bold cyan] [bold]{entry.func_name}[/bold]{copied_mark}")


def run_repl(workspace: Workspace) -> None:
    """REPL loop"""
    title_text = f"[bold green]{CONSOLE_TITLE}[/bold green] - Workspace: {workspace.root_path}"
    console.print(Panel(title_text, title=CONSOLE_TITLE))
    console.print(f"[dim]Workspace: {workspace.root_path}[/dim]")
    console.print(HELP_MESSAGE)
    console.print("[dim]Type /help for commands, /quit to exit.[/dim]\n")

    while True:
        user_input = _read_multiline_input()

        if not user_input.strip():
            continue

        parsed = parse_input(user_input)

        if parsed.is_command:
            handle_command(workspace, parsed)
        else:
            handle_tool_call(workspace, parsed)


def _read_multiline_input() -> str:
    """Read input, support multi-line for func_call"""
    first_line = Prompt.ask(f"[bold blue]{CONSOLE_TITLE}>[/bold blue]")

    if not first_line.strip():
        return first_line

    if not (first_line.startswith("<func_call>") and first_line.endswith("</func_call>")):
        return first_line

    if first_line.endswith("</func_call>"):
        return first_line

    lines = [first_line]
    while True:
        cont_line = Prompt.ask("[dim]... [/dim]")
        lines.append(cont_line)
        if cont_line.strip().endswith("</func_call>"):
            break

    return "\n".join(lines)


def handle_command(workspace: Workspace, parsed) -> None:
    """Handle commands"""
    cmd = parsed.command_type

    if cmd == "quit":
        console.print("[bold]Goodbye![/bold]")
        sys.exit(0)

    if cmd == "help":
        console.print(Panel(HELP_MESSAGE, title="Help"))
        return

    if cmd == "tools":
        list_tools()
        return

    if cmd == "tool":
        name = parsed.func_kwargs.get("name")
        if name:
            show_tool_details(name)
        return

    if cmd == "prompt":
        prompt = generate_tool_prompt()
        entry = result_manager.add("tool_prompt", prompt)

        lines_count = prompt.count("\n") + 1
        title = (
            f"[bold cyan]##{entry.index}[/bold cyan] [bold green]tool_prompt[/bold green] "
            + f"[yellow]({lines_count} lines)[/yellow]"
        )

        add_to_viewer(str(entry.index), title, prompt, "markdown")
        console.print(f"[dim]✓ Tool prompt ##{entry.index} added to viewer.[/dim]")
        return

    if cmd == "workspace":
        prompt = generate_workspace_prompt(workspace)
        entry = result_manager.add("workspace_prompt", prompt)

        lines_count = prompt.count("\n") + 1
        title = (
            f"[bold cyan]##{entry.index}[/bold cyan] [bold green]workspace_prompt[/bold green]"
            + f" [yellow]({lines_count} lines)[/yellow]"
        )

        add_to_viewer(str(entry.index), title, prompt)
        console.print(f"[dim]✓ Workspace prompt ##{entry.index} added to viewer.[/dim]")
        return

    if cmd == "history":
        show_history()
        return

    if cmd == "copy":
        index = parsed.func_kwargs.get("index")

        if index is None:
            history = result_manager.list_history()
            if not history:
                console.print("[yellow]No history to copy.[/yellow]")
                return
            index = history[-1].index

        if result_manager.copy_to_clipboard(index):
            console.print(f"[green]Result #{index} copied to clipboard.[/green]")
        else:
            console.print(f"[red]Failed to copy result #{index}.[/red]")
        return

    if cmd == "view":
        # 新增:打开交互式查看器
        run_viewer()
        return

    if cmd == "view_clear":
        # 新增:清空查看器
        clear_viewer()
        console.print("[green]Viewer cleared.[/green]")
        return

    if cmd == "view_remove":
        # 新增:移除指定项目
        index = parsed.func_kwargs.get("index")
        if index:
            viewer = get_viewer()
            if viewer.remove_item(str(index)):
                console.print(f"[green]Item #{index} removed from viewer.[/green]")
            else:
                console.print(f"[yellow]Item #{index} not found in viewer.[/yellow]")
        return


def handle_tool_call(workspace: Workspace, parsed) -> None:
    """Handle tool calls"""
    func_name, func_args, func_kwargs, result = execute_tool_call(parsed.raw_input)
    entry = result_manager.add(func_name, result)

    result_str = str(result)
    lines_count = result_str.count("\n") + 1

    # 创建标题
    title = _create_result_title(entry.index, func_name, func_args, func_kwargs, lines_count)

    # 检测语言
    language = None
    if func_name == "read_file":
        file_path = ""
        if func_args and isinstance(func_args[0], str):
            file_path = func_args[0]
        elif "file_path" in func_kwargs:
            file_path = func_kwargs["file_path"]
        language = _detect_language(file_path)

    # 添加到查看器
    add_to_viewer(str(entry.index), title, result_str, language)

    # 显示简短的提示
    console.print(f"[dim]✓ Result ##{entry.index} added to viewer.[/dim]")

    # 自动运行查看器的选项(可通过环境变量控制)
    auto_view = os.getenv("MANUALAID_AUTO_VIEW", "").lower() in ("true", "1", "yes", "on")
    if auto_view:
        run_viewer()

    if result_manager.AUTO_COPY and not func_name.startswith(("tool_prompt", "workspace_prompt")):
        console.print("[dim](Auto-copied to clipboard)[/dim]")


def _format_tool_params(args: list, kwargs: dict) -> str:
    """格式化工具参数为简洁的字符串"""
    parts = []

    # 处理位置参数
    for arg in args:
        if isinstance(arg, str):
            # 截断长字符串
            arg_str = arg if len(arg) <= 30 else f"{arg[:27]}..."
            parts.append(f'"{arg_str}"')
        else:
            parts.append(str(arg))

    # 处理关键字参数
    for key, value in kwargs.items():
        if isinstance(value, str):
            val_str = value if len(value) <= 30 else f"{value[:27]}..."
            parts.append(f'{key}="{val_str}"')
        else:
            parts.append(f"{key}={value}")

    if not parts:
        return "no parameters"

    params_str = ", ".join(parts)
    # 如果参数太长,截断
    if len(params_str) > 50:
        params_str = params_str[:47] + "..."

    return params_str


def _detect_language(file_path: str) -> str:
    """检测文件语言"""
    ext_map = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".jsx": "javascript",
        ".tsx": "typescript",
        ".json": "json",
        ".html": "html",
        ".css": "css",
        ".md": "markdown",
        ".yml": "yaml",
        ".yaml": "yaml",
        ".toml": "toml",
        ".sh": "bash",
        ".sql": "sql",
        ".xml": "xml",
        ".ini": "ini",
        ".cfg": "ini",
    }
    for ext, lang in ext_map.items():
        if file_path.lower().endswith(ext):
            return lang
    return "text"


def _create_result_title(index: int, func_name: str, args: list, kwargs: dict, lines_count: int) -> str:
    """创建结果标题(Rich markup 格式)"""
    params_str = _format_tool_params(args, kwargs)
    return (
        f"[bold cyan]##{index}[/bold cyan] [bold green]{func_name}[/bold green]([dim]{params_str}[/dim])"
        + f" [yellow]({lines_count} lines)[/yellow]"
    )


def main() -> None:
    """Main entry point"""
    workspace = init_workspace()
    if workspace:
        run_repl(workspace)


if __name__ == "__main__":
    main()
