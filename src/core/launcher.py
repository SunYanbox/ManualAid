import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from rich.panel import Panel


def _is_frozen() -> bool:
    """检测是否在 PyInstaller 打包环境中运行"""
    return getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")


def _get_executable_path() -> str:
    """获取当前可执行文件路径(支持开发环境和打包环境)"""
    if _is_frozen():
        # PyInstaller 打包环境:返回 exe 路径
        return sys.executable
    else:
        # 开发环境:返回 Python 解释器路径
        return sys.executable


def _get_script_path() -> str:
    """获取要运行的脚本/模块路径"""
    if _is_frozen():
        # 打包环境:不需要额外参数,exe 本身就是程序
        return ""
    else:
        # 开发环境:使用入口文件名
        return "main.py"


def _get_base_command(workspace_path: str | None = None) -> list[str]:
    """构建基础命令(根据环境自动选择)"""
    executable = _get_executable_path()
    script = _get_script_path()

    base_cmd = [executable] if _is_frozen() else [executable, script]

    # 添加工作区路径参数
    if workspace_path:
        base_cmd.extend(["-p", str(Path(workspace_path).absolute())])

    return base_cmd


def _get_launch_command(workspace_path: str | None = None) -> list[str]:
    """获取当前平台的完整启动命令(包括终端启动器)"""
    base_cmd = _get_base_command(workspace_path)

    # 平台特定的终端启动器
    if sys.platform == "win32":
        # Windows: 使用 start 命令打开新 cmd 窗口
        # 注意:start 是 cmd 内部命令,需要 shell=True
        return ["start", "cmd", "/k", *base_cmd]

    elif sys.platform == "darwin":
        # macOS: 使用 AppleScript 打开新 Terminal 窗口
        # 转义参数中的空格
        cmd_str = " ".join(f'"{arg}"' if " " in arg else arg for arg in base_cmd)
        applescript = f'tell application "Terminal" to do script "{cmd_str}"'
        return ["osascript", "-e", applescript]

    else:  # Linux 和其他 Unix-like 系统
        # 尝试查找可用的终端模拟器
        terminals = [
            ["gnome-terminal", "--"],
            ["konsole", "-e"],
            ["xfce4-terminal", "-x"],
            ["terminator", "-x"],
            ["xterm", "-e"],
        ]

        for term_cmd in terminals:
            # 检查终端模拟器是否存在
            # noinspection PyDeprecation
            if shutil.which(term_cmd[0]):
                return term_cmd + base_cmd

        # 回退方案:在当前终端后台运行
        return ["nohup", *base_cmd, "&"]


def launch(path: str, console: Any) -> bool:
    # 如果未提供路径,使用当前工作区
    # 验证路径
    path_obj = Path(path).resolve()
    if not path_obj.exists():
        console.print(f"[bold red]错误: 路径不存在: {path_obj}[/bold red]")
        raise Exception(f"Path not found: {path}")
    if not path_obj.is_dir():
        console.print(f"[bold red]错误: 路径不是目录: {path_obj}[/bold red]")
        raise Exception(f"Not a directory: {path_obj}")
    workspace_path = str(path_obj)

    try:
        launch_cmd = _get_launch_command(workspace_path)

        # 显示启动信息
        message = "[dim]运行模式: 打包可执行文件[/dim]" if _is_frozen() else "[dim]运行模式: 开发环境 (Python)[/dim]"
        message += "\n" + f"[dim]启动命令: {' '.join(launch_cmd)}[/dim]\n"

        # 执行启动命令
        if sys.platform == "win32":
            # Windows: start 命令需要 shell=True
            subprocess.Popen(" ".join(launch_cmd), shell=True)
        else:
            # Unix-like: 直接执行
            subprocess.Popen(launch_cmd)

        if workspace_path:
            message += f"[dim]工作区: {workspace_path}[/dim]"

        console.print(Panel(message, title="[green]✓ 已启动新的 ManualAid 窗口[/green]"))

        return True

    except Exception as e:
        error_msg = f"启动新窗口失败: {e}"
        console.print(f"[bold red]{error_msg}[/bold red]")

        # 显示手动启动帮助
        if _is_frozen():
            manual_cmd = f'"{_get_executable_path()}" -p "{workspace_path}"'
        else:
            manual_cmd = f'python main.py -p "{workspace_path}"'

        info_panel = Panel(
            f"[yellow]手动启动命令:[/yellow]\n{manual_cmd}\n\n[dim]请在新终端中手动运行以上命令[/dim]",
            title="启动失败",
            border_style="red",
        )
        console.print(info_panel)

        return False
