"""ManualAid Console - Rich-based TUI console tool"""

import argparse
import sys
from pathlib import Path

from rich.console import Console

from src.console.folder_picker import pick_folder
from src.console.result_manager import ResultManager
from src.console.ui.repl import REPL
from src.core.tool_registry import ToolRegistry
from src.workspace.workspace import Workspace

console = Console()
tool_registry = ToolRegistry()


def init_workspace(start_path: str | None = None) -> Workspace | None:
    """Initialize workspace"""
    if start_path:
        folder_path = Path(start_path).resolve()
        if not folder_path.exists():
            console.print(f"[bold red]Path does not exist: {folder_path}[/bold red]")
            sys.exit(1)
        if not folder_path.is_dir():
            console.print(f"[bold red]Path is not a directory: {folder_path}[/bold red]")
            sys.exit(1)
        console.print(f"[green]Workspace:[/green] {folder_path}")
    else:
        folder_path = pick_folder()
        if not folder_path:
            console.print("[bold red]No folder selected. Exiting.[/bold red]")
            sys.exit(0)
        console.print(f"[green]Workspace:[/green] {folder_path}")

    workspace: Workspace = Workspace(str(folder_path))

    tool_registry.register(workspace)

    return workspace


def main() -> None:
    """Main entry point"""
    parser = argparse.ArgumentParser(description="ManualAid Console - Rich-based TUI console tool")
    parser.add_argument("-p", "--path", type=str, help="Working directory path (skips folder picker dialog)")
    args = parser.parse_args()

    workspace = init_workspace(args.path)
    if workspace:
        result_manager = ResultManager()
        result_manager.console = console
        repl = REPL(workspace, tool_registry, result_manager, console)
        repl.run()


if __name__ == "__main__":
    main()
