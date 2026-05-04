from pathlib import Path

from src.core.file_tracker import FileTracker
from src.models.tool_error_response import ToolErrorResponse
from src.utils.binary_detector import is_binary_file
from src.workspace.tools.base_tool import BaseTool
from src.workspace.workspace import Workspace


class WriteTool(BaseTool):
    def __init__(self, workspace: Workspace):
        super().__init__(workspace, "write", self.write.__doc__, write_permission=True)
        self.func = self.write
        self.params = BaseTool.extract_params(self.write)
        self.param_descriptions = {
            "path": "文件路径",
            "content": "写入内容",
        }

    @BaseTool.handle_tool_exceptions
    def write(self, path: str, content: str = "") -> str:
        """
        写入文件内容, 如文件不存在则创建(含父目录)
        """
        source_path = Path(path)
        path: Path = self.workspace.path_validator.resolve_path(source_path)

        if path.exists() and path.is_dir():
            return ToolErrorResponse(self.__class__.__name__, ValueError(f"路径 {path} 是一个目录,无法写入")).to_str()

        if is_binary_file(path):
            return ToolErrorResponse(
                self.__class__.__name__,
                ValueError(f"禁止写入二进制文件: {path}"),
            ).to_str()

        mtime_error = self._validate_mtime(path)
        if mtime_error:
            return mtime_error

        old_content = ""
        old_meta = None
        if path.exists() and path.is_file():
            old_meta = FileTracker.get_file_meta(path)
            try:
                old_content = path.read_text(encoding="utf-8")
            except Exception:
                old_content = ""

        rel_path = str(path.relative_to(self.workspace.root_path))
        old_hash = old_meta.get("checksum") if old_meta else None
        new_hash = FileTracker.compute_checksum_from_string(content)
        diff_content = self._generate_diff(old_content, content, rel_path)

        session_id = self.workspace._current_session_id
        snapshot_id = self.workspace.db.record_file_snapshot(
            rel_path,
            old_hash,
            new_hash,
            diff_content,
            audit_status="PENDING_AUDIT",
            session_id=session_id,
            pending_content=content,
        )

        return f"[Write Preview]\nFile: {rel_path}\nSnapshot ID: {snapshot_id}\nDiff:\n{diff_content}"
