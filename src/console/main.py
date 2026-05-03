"""ManualAid 控制台 -- 基于 Textual 的 TUI 工具"""

import argparse
import atexit
import contextlib
import os
import sys
import threading
import time
from pathlib import Path

from dotenv import load_dotenv

from src.console.folder_picker import pick_folder
from src.console.result_manager import ResultManager
from src.console.ui.repl import REPL
from src.core.tool_registry import ToolRegistry
from src.workspace.workspace import Workspace

tool_registry = ToolRegistry()

# Session heartbeat: periodically persists session duration so that abnormal
# termination (window close, Ctrl+C, SIGKILL) loses minimal data.
_session_heartbeat_stop: threading.Event | None = None


def _session_heartbeat(
    db,
    session_id: int,
    stop_event: threading.Event,
    interval: float,
) -> None:
    """定期守护删除标志并持久化会话时长.

    每隔 interval 秒(默认 5 秒):
    1. 如果删除标志被错误地设置为 1,则将其恢复
    2. 每第 6 个周期(约 30 秒)持久化一次会话时长
    """
    cycle = 0
    while not stop_event.wait(interval):
        cycle += 1
        with contextlib.suppress(Exception):
            # Guard against accidental deletion flag
            db.restore_session_deleted_flag(session_id)
            # Persist duration every 6 cycles
            if cycle % 6 == 0:
                db.update_session_duration(session_id)


def _cleanup_orphaned_sessions(db) -> None:
    """为所有孤立会话安排异步删除.

    扫描每个会话,对于在相关表中没有关联数据的任何会话,启动轮询删除
    异步机制确保如果另一个实例的心跳恢复了该标志,删除操作会被安全取消
    """
    for session_row in db.get_all_sessions():
        sid = session_row[0]
        if db.is_session_orphaned(sid):
            db.delete_session_async(sid)


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

    # 在创建新会话之前清理孤立的会话
    _cleanup_orphaned_sessions(workspace.db)

    session_id = workspace.db.create_session(name=f"session_{time.strftime('%Y%m%d_%H%M%S')}")
    tool_registry.set_session_id(session_id)
    workspace._current_session_id = session_id

    # Start a daemon heartbeat thread to periodically persist session duration
    # and guard against accidental deletion flag
    global _session_heartbeat_stop
    _session_heartbeat_stop = threading.Event()
    interval = int(os.getenv("SESSION_FLAG_CHECK_INTERVAL", "5"))
    thread = threading.Thread(
        target=_session_heartbeat,
        args=(workspace.db, session_id, _session_heartbeat_stop, interval),
        daemon=True,
    )
    thread.start()

    atexit.register(_cleanup, workspace, session_id)

    return workspace


def _cleanup(workspace: Workspace, session_id: int) -> None:
    global _session_heartbeat_stop
    if _session_heartbeat_stop is not None:
        _session_heartbeat_stop.set()
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
