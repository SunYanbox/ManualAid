"""ManualAid Console - Rich-based TUI console tool"""

import sys

from rich.console import Console

from src.console.folder_picker import pick_folder
from src.console.result_manager import ResultManager
from src.console.ui.repl import REPL
from src.core.tool_registry import ToolRegistry
from src.workspace.workspace import Workspace

console = Console()
tool_registry = ToolRegistry()


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
    tool_registry.register_function(workspace.write)
    tool_registry.register_function(workspace.search_content)
    tool_registry.register_function(workspace.read_file_lines)

    return workspace


def main() -> None:
    """Main entry point"""
    workspace = init_workspace()
    if workspace:
        result_manager = ResultManager()
        repl = REPL(workspace, tool_registry, result_manager, console)
        repl.run()


if __name__ == "__main__":
    main()
