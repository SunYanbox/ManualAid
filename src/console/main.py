"""ManualAid 控制台 -- 基于 Textual 的 TUI 工具"""

import argparse
import atexit
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

from src.console.folder_picker import pick_folder
from src.console.result_manager import ResultManager
from src.console.ui.repl import REPL
from src.core.tool_registry import ToolRegistry
from src.workspace.workspace import Workspace

tool_registry = ToolRegistry()


def init_workspace(start_path: str | None = None) -> Workspace | None:
    """初始化工作区"""
    if start_path:
        folder_path = Path(start_path).resolve()
        if not folder_path.exists():
            print(f"路径不存在: {folder_path}")
            sys.exit(1)
        if not folder_path.is_dir():
            print(f"路径不是目录: {folder_path}")
            sys.exit(1)
        print(f"工作区: {folder_path}")
    else:
        folder_path = pick_folder()
        if not folder_path:
            print("未选择文件夹,退出.")
            sys.exit(0)
        print(f"工作区: {folder_path}")

    workspace: Workspace = Workspace(str(folder_path))
    tool_registry.register(workspace)

    session_id = workspace.db.create_session(name=f"session_{time.strftime('%Y%m%d_%H%M%S')}")
    tool_registry.set_session_id(session_id)
    workspace._current_session_id = session_id

    atexit.register(_cleanup, workspace, session_id)

    return workspace


def _cleanup(workspace: Workspace, session_id: int) -> None:
    if session_id and hasattr(workspace, "db"):
        workspace.db.close_session(session_id)
        workspace.db.close()


def main() -> None:
    """主入口"""
    load_dotenv()
    parser = argparse.ArgumentParser(description="ManualAid 控制台 -- 基于 Textual 的 TUI 工具")
    parser.add_argument("-p", "--path", type=str, help="工作目录路径(跳过文件夹选择对话框)")
    args = parser.parse_args()

    workspace = init_workspace(args.path)
    if workspace:
        result_manager = ResultManager()
        # 启动 Textual 应用(不再需要显式传入 console)
        app = REPL(workspace, tool_registry, result_manager)
        app.run()


if __name__ == "__main__":
    main()
