"""会话管理器 -- 管理 .ManualAid 目录和会话生命周期."""

import json
import threading
import time
import uuid
from pathlib import Path
from typing import ClassVar

from src.constants.manual_aid import (
    MANUALAID_DIR,
    PATCHES_DIR,
    READ_RECORDS_FILE,
    SESSION_FILE,
    SESSIONS_DIR,
    TOOL_CALLS_FILE,
)


class SessionManager:
    """管理 .ManualAid 目录和会话生命周期.

    每个工作区根目录对应一个 SessionManager 单例.
    会话以目录隔离,方便清理和归档.
    """

    _instances: ClassVar[dict[str, "SessionManager"]] = {}
    _instances_lock: ClassVar[threading.Lock] = threading.Lock()

    def __new__(cls, workspace_root: str | Path) -> "SessionManager":
        workspace_root = str(Path(workspace_root).resolve())
        with cls._instances_lock:
            if workspace_root not in cls._instances:
                instance = super().__new__(cls)
                instance._initialized = False
                cls._instances[workspace_root] = instance
        return cls._instances[workspace_root]

    def __init__(self, workspace_root: str | Path) -> None:
        if self._initialized:
            return

        self._workspace_root = Path(workspace_root).resolve()
        self._manual_dir = self._workspace_root / MANUALAID_DIR
        self._session_id: str | None = None
        self._session_dir: Path | None = None
        self._session_started_at: str | None = None
        self._lock = threading.Lock()
        self._initialized = True

    # ------------------------------------------------------------------
    # 属性访问器
    # ------------------------------------------------------------------

    @property
    def manual_dir(self) -> Path:
        """.ManualAid 目录路径."""
        return self._manual_dir

    @property
    def session_id(self) -> str | None:
        """当前会话 ID."""
        return self._session_id

    @property
    def session_dir(self) -> Path | None:
        """当前会话目录路径."""
        return self._session_dir

    @property
    def sessions_root(self) -> Path:
        """所有会话的根目录."""
        return self._manual_dir / SESSIONS_DIR

    # ------------------------------------------------------------------
    # 会话生命周期
    # ------------------------------------------------------------------

    def create_session(self) -> str:
        """创建新会话,返回 session_id.

        会话 ID 格式: {YYYYMMDD}-{HHMMSS}-{uuid短码8位}
        """
        with self._lock:
            if self._session_id is not None:
                raise RuntimeError("当前已有活动会话,请先关闭再创建")

            now = time.localtime()
            date_part = time.strftime("%Y%m%d", now)
            time_part = time.strftime("%H%M%S", now)
            short_uuid = uuid.uuid4().hex[:8]
            self._session_id = f"{date_part}-{time_part}-{short_uuid}"

            self._session_dir = self.sessions_root / self._session_id
            patches_dir = self._session_dir / PATCHES_DIR

            # 创建目录结构
            patches_dir.mkdir(parents=True, exist_ok=True)

            self._session_started_at = time.strftime("%Y-%m-%dT%H:%M:%S", now)

            # 写入初始 session.json
            self._write_session_json(
                {
                    "session_id": self._session_id,
                    "workspace_root": str(self._workspace_root),
                    "started_at": self._session_started_at,
                    "ended_at": None,
                    "tool_stats": {},
                }
            )

            return self._session_id

    def close_session(self) -> None:
        """关闭当前会话,写入结束时间."""
        with self._lock:
            if self._session_id is None:
                return

            session_data = self._read_session_json()
            if session_data is not None:
                session_data["ended_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
                self._write_session_json(session_data)

            self._session_id = None
            self._session_started_at = None

    def is_session_active(self) -> bool:
        """检查是否有活动会话."""
        return self._session_id is not None

    def ensure_session(self) -> str:
        """确保存在活动会话,若不存在则创建,返回 session_id."""
        if not self.is_session_active():
            return self.create_session()
        return self._session_id  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # 工具调用日志 (JSONL)
    # ------------------------------------------------------------------

    def append_tool_call(self, record: dict) -> None:
        """追加一条工具调用记录到 tool_calls.jsonl.

        Args:
            record: 工具调用记录字典,必须包含 call_id, timestamp, func_name 等字段.
        """
        if not self.is_session_active():
            raise RuntimeError("没有活动会话,无法记录工具调用")

        with self._lock:
            calls_path = self._session_dir / TOOL_CALLS_FILE  # type: ignore[union-attr]
            line = json.dumps(record, ensure_ascii=False) + "\n"
            with open(calls_path, "a", encoding="utf-8") as f:
                f.write(line)

    def get_tool_calls(self) -> list[dict]:
        """获取当前会话所有工具调用记录."""
        if not self.is_session_active():
            return []

        calls_path = self._session_dir / TOOL_CALLS_FILE  # type: ignore[union-attr]
        if not calls_path.exists():
            return []

        records: list[dict] = []
        with open(calls_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records

    # ------------------------------------------------------------------
    # 读取记录簿
    # ------------------------------------------------------------------

    def update_read_record(self, file_path: str, meta: dict) -> None:
        """更新读取记录簿中的文件元数据.

        Args:
            file_path: 相对于工作区根目录的文件路径.
            meta: 包含 mtime, size, sha256 等字段的字典.
        """
        if not self.is_session_active():
            raise RuntimeError("没有活动会话,无法更新读取记录")

        with self._lock:
            records = self._load_read_records()
            records[file_path] = meta
            self._save_read_records(records)

    def get_read_record(self, file_path: str) -> dict | None:
        """获取指定文件的读取记录.

        Args:
            file_path: 相对于工作区根目录的文件路径.

        Returns:
            文件元数据字典,若无记录返回 None.
        """
        records = self._load_read_records()
        return records.get(file_path)

    def has_read_record(self, file_path: str) -> bool:
        """检查是否有指定文件的读取记录."""
        return self.get_read_record(file_path) is not None

    # ------------------------------------------------------------------
    # Patch 文件管理
    # ------------------------------------------------------------------

    def get_patches_dir(self) -> Path:
        """获取当前会话的 patches 目录."""
        if not self.is_session_active():
            raise RuntimeError("没有活动会话")
        return self._session_dir / PATCHES_DIR  # type: ignore[union-attr]

    def save_patch(self, call_id: str, patch_content: str) -> Path:
        """保存 diff patch 文件.

        Args:
            call_id: 工具调用 ID.
            patch_content: unified diff 格式的 patch 内容.

        Returns:
            保存的 patch 文件路径.
        """
        patches_dir = self.get_patches_dir()
        patch_path = patches_dir / f"{call_id}.patch"
        patch_path.write_text(patch_content, encoding="utf-8")
        return patch_path

    def load_patch(self, call_id: str) -> str | None:
        """加载指定 call_id 的 patch 文件内容."""
        patches_dir = self.get_patches_dir()
        patch_path = patches_dir / f"{call_id}.patch"
        if not patch_path.exists():
            return None
        return patch_path.read_text(encoding="utf-8")

    # ------------------------------------------------------------------
    # 会话元数据
    # ------------------------------------------------------------------

    def update_session_stats(self, tool_stats: dict) -> None:
        """更新 session.json 中的工具统计.

        Args:
            tool_stats: {func_name: {calls, failures, total_duration_ms}} 格式的字典.
        """
        if not self.is_session_active():
            return

        with self._lock:
            session_data = self._read_session_json()
            if session_data is not None:
                session_data["tool_stats"] = tool_stats
                self._write_session_json(session_data)

    # ------------------------------------------------------------------
    # 历史会话查询
    # ------------------------------------------------------------------

    def list_sessions(self) -> list[dict]:
        """列出所有历史会话摘要."""
        sessions: list[dict] = []
        if not self.sessions_root.exists():
            return sessions

        for session_dir in sorted(self.sessions_root.iterdir(), reverse=True):
            if not session_dir.is_dir():
                continue
            session_file = session_dir / SESSION_FILE
            if session_file.exists():
                try:
                    data = json.loads(session_file.read_text(encoding="utf-8"))
                    sessions.append(data)
                except (json.JSONDecodeError, OSError):
                    continue

        return sessions

    # ------------------------------------------------------------------
    # 内部辅助方法
    # ------------------------------------------------------------------

    def _write_session_json(self, data: dict) -> None:
        """写入 session.json."""
        session_path = self._session_dir / SESSION_FILE  # type: ignore[union-attr]
        session_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _read_session_json(self) -> dict | None:
        """读取 session.json."""
        session_path = self._session_dir / SESSION_FILE  # type: ignore[union-attr]
        if not session_path.exists():
            return None
        return json.loads(session_path.read_text(encoding="utf-8"))

    def _load_read_records(self) -> dict:
        """加载读取记录簿."""
        if not self.is_session_active():
            return {}
        records_path = self._session_dir / READ_RECORDS_FILE  # type: ignore[union-attr]
        if not records_path.exists():
            return {}
        try:
            return json.loads(records_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    def _save_read_records(self, records: dict) -> None:
        """保存读取记录簿."""
        records_path = self._session_dir / READ_RECORDS_FILE  # type: ignore[union-attr]
        records_path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")

    # ------------------------------------------------------------------
    # 测试辅助
    # ------------------------------------------------------------------

    @classmethod
    def reset_all(cls) -> None:
        """重置所有单例(仅用于测试)."""
        with cls._instances_lock:
            cls._instances.clear()
