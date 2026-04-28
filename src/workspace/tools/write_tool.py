import difflib
from pathlib import Path

from src.core.file_tracker import FileTracker
from src.models.tool_error_response import ToolErrorResponse
from src.workspace.path_validator import PathNotFoundError, WorkspaceBoundaryError
from src.workspace.tools.base_tool import BaseTool
from src.workspace.workspace import Workspace


class WriteTool(BaseTool):
    def __init__(self, workspace: Workspace):
        super().__init__(workspace, "write", self.write.__doc__, write_permission=True)
        self.func = self.write
        self.params = BaseTool.extract_params(self.write)

    def write(self, file_path: str, content: str = "") -> str:
        """
        写入文件内容,如文件不存在则创建(含父目录)

        Parameters
        ----------
        file_path: 文件路径
        content: 写入内容
        """
        try:
            source_file_path = Path(file_path)
            file_path: Path = self.workspace.path_validator.resolve_path(source_file_path)

            if file_path.exists() and file_path.is_dir():
                return ToolErrorResponse(
                    self.__class__.__name__, ValueError(f"路径 {file_path} 是一个目录,无法写入")
                ).to_str()

            mtime_error = self._validate_mtime(file_path)
            if mtime_error:
                return mtime_error

            old_content = ""
            old_meta = None
            if file_path.exists() and file_path.is_file():
                old_meta = FileTracker.get_file_meta(file_path)
                try:
                    old_content = file_path.read_text(encoding="utf-8")
                except Exception:
                    old_content = ""

            self.workspace.path_validator.create_file_with_parents(file_path, content)

            self._record_write_snapshot(file_path, old_meta, old_content, content)

            return "write success"
        except PathNotFoundError as err1:
            return ToolErrorResponse(self.__class__.__name__, err1).to_str()
        except WorkspaceBoundaryError as err2:
            return ToolErrorResponse(self.__class__.__name__, err2).to_str()
        except PermissionError as err3:
            return ToolErrorResponse(self.__class__.__name__, err3).to_str()
        except Exception as err:
            return ToolErrorResponse(self.__class__.__name__, err).to_str()

    def _validate_mtime(self, resolved_path: Path) -> str | None:
        if not resolved_path.exists():
            return None

        rel_path = str(resolved_path.relative_to(self.workspace.root_path))
        record = self.workspace.db.get_file_read_record(rel_path)
        if record is None:
            return None

        stored_mtime = record[2]
        current_mtime = resolved_path.stat().st_mtime

        if abs(current_mtime - stored_mtime) > 0.001:
            return (
                f'ERROR: FILE_MODIFIED_EXTERNALLY - '
                f'The file "{rel_path}" was modified externally since last read. '
                f'Please re-read the file with the "read" tool before writing to it.'
            )
        return None

    def _record_write_snapshot(
        self, resolved_path: Path, old_meta: dict | None, old_content: str, new_content: str
    ) -> None:
        try:
            rel_path = str(resolved_path.relative_to(self.workspace.root_path))
            old_hash = old_meta.get("checksum") if old_meta else None
            new_hash = FileTracker.compute_checksum_from_string(new_content)
            diff_content = self._generate_diff(old_content, new_content, rel_path)

            session_id = self.workspace._current_session_id
            self.workspace.db.record_file_snapshot(
                rel_path, old_hash, new_hash, diff_content, audit_status="PENDING_AUDIT", session_id=session_id
            )

            new_meta = FileTracker.get_file_meta(resolved_path)
            if new_meta:
                self.workspace.db.record_file_read(rel_path, new_meta["mtime"], new_meta["size"], new_meta["checksum"])
        except Exception:
            pass

    @staticmethod
    def _generate_diff(old_content: str, new_content: str, file_path: str) -> str:
        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)
        diff = difflib.unified_diff(old_lines, new_lines, fromfile=f"a/{file_path}", tofile=f"b/{file_path}")
        return "".join(diff)
