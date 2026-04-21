import subprocess
import sys
from pathlib import Path

from rich.panel import Panel

from src.console.commands.base import Command, CommandContext, CommandResult


def _get_launch_command(workspace_path: str | None = None) -> list[str]:
    """Get the appropriate launch command for the current platform / 获取当前平台的适当启动命令"""
    python_exe = sys.executable
    script_path = "src.console.main"

    # Build base command / 构建基础命令
    base_cmd = [python_exe, "-m", str(script_path)]
    if workspace_path:
        base_cmd.extend(["-p", str(Path(workspace_path).absolute())])

    # Platform-specific terminal launcher / 特定平台的终端启动器
    if sys.platform == "win32":
        # Windows: start new cmd window
        return ["start", "cmd", "/k", *base_cmd]
    elif sys.platform == "darwin":
        # macOS: open new Terminal window
        # macOS:打开新的终端窗口
        # Escape spaces in path for AppleScript
        # 为 AppleScript 转义路径中的空格
        cmd_str = " ".join(f'"{arg}"' if " " in arg else arg for arg in base_cmd)
        applescript = f'tell application "Terminal" to do script "{cmd_str}"'
        return ["osascript", "-e", applescript]
    else:
        # Linux: try various terminal emulators
        # Linux:尝试多种终端模拟器
        terminals = [
            ["gnome-terminal", "--"],
            ["konsole", "-e"],
            ["xfce4-terminal", "-x"],
            ["terminator", "-x"],
            ["xterm", "-e"],
        ]

        for term_cmd in terminals:
            # Check if terminal emulator exists
            # 检查终端模拟器是否存在
            if subprocess.run(["which", term_cmd[0]], capture_output=True, text=True).returncode == 0:
                return term_cmd + base_cmd

        # Fallback: just run in current terminal with nohup
        # 回退方案:直接在当前终端中使用 nohup 运行
        return ["nohup", *base_cmd, "&"]


class NewWindowCommand(Command):
    """Launch a new terminal window running ManualAid with specified workspace

    启动一个新终端窗口,运行带有指定工作区的 ManualAid"""

    def __init__(self):
        super().__init__()
        self.name = "new"
        self.aliases = ["/new", "/n"]
        self.description = "Launch a new terminal window with ManualAid (optional workspace path)"
        self.usage = "/new [path]"

    def execute(self, context: CommandContext) -> CommandResult:
        # Parse workspace path from command / 从命令中解析工作区路径
        parts = context.parsed_input.source.split()
        workspace_path = parts[1] if len(parts) >= 2 else None

        # If no path provided, use current workspace / 如果未提供路径,则使用当前工作区
        if not workspace_path:
            workspace_path = str(context.workspace.root_path)

        # Validate path if provided / 若提供路径,则对其进行验证
        if workspace_path:
            path_obj = Path(workspace_path).resolve()
            if not path_obj.exists():
                context.console.print(f"[bold red]Error: Path does not exist: {path_obj}[/bold red]")
                return CommandResult(success=False, message=f"Path not found: {workspace_path}")
            if not path_obj.is_dir():
                context.console.print(f"[bold red]Error: Path is not a directory: {path_obj}[/bold red]")
                return CommandResult(success=False, message=f"Not a directory: {workspace_path}")
            workspace_path = str(path_obj)

        try:
            launch_cmd = _get_launch_command(workspace_path)

            if sys.platform == "win32":
                # Windows: use shell=True for 'start' command
                subprocess.Popen(" ".join(launch_cmd), shell=True)
            else:
                # Unix-like: direct execution
                subprocess.Popen(launch_cmd)

            context.console.print("[green]✓ New ManualAid window launched[/green]")
            if workspace_path:
                context.console.print(f"[dim]Workspace: {workspace_path}[/dim]")

            return CommandResult(success=True, message="New window launched")

        except Exception as e:
            error_msg = f"Failed to launch new window: {e}"
            context.console.print(f"[bold red]{error_msg}[/bold red]")

            # Show helpful info on failure
            info_panel = Panel(
                f"[yellow]Manual launch command:[/yellow]\n"
                f'python -m src.console.main -p "{workspace_path}"\n\n'
                f"[dim]Try running this in a new terminal manually.[/dim]",
                title="Launch Failed",
                border_style="red",
            )
            context.console.print(info_panel)

            return CommandResult(success=False, message=error_msg)
