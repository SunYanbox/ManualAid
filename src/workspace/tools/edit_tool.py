"""安全的字符串替换编辑工具 — 只发布待审核更改."""

from pathlib import Path

from src.models.tool_error_response import ToolErrorResponse
from src.workspace.tools.base_tool import BaseTool
from src.workspace.workspace import Workspace


class EditTool(BaseTool):
    """安全的字符串替换编辑工具 — 两阶段提交 (预览 → 审核确认).

    只计算 diff 并记录 PENDING_AUDIT 快照,不直接修改磁盘.
    由审核提交模块 (AuditCommitter) 在批准后执行实际写入.
    """

    def __init__(self, workspace: Workspace):
        super().__init__(workspace, "edit", self.edit.__doc__, write_permission=True)
        self.func = self.edit
        self.params = BaseTool.extract_params(self.edit)

    @BaseTool.handle_tool_exceptions
    def edit(
        self,
        file_path: str,
        old_string: str,
        new_string: str,
        max_replacements: int = 10,
        context_before: str = "",
        context_after: str = "",
    ) -> str:
        """
        在文件中进行安全的字符串替换(仅预览,不修改磁盘)

        执行 dry-run 替换,生成 diff,记录 PENDING_AUDIT 快照.
        批准后由 AuditCommitter 执行实际写入.

        Parameters
        ----------
        file_path: 文件路径
        old_string: 待替换的字符串(不能为空)
        new_string: 替换后的字符串
        max_replacements: 最大替换次数(默认 10,最大 100)
        context_before: 匹配前的上下文文本(可选,用于校验)
        context_after: 匹配后的上下文文本(可选,用于校验)
        """
        # 1. 参数校验
        if not old_string:
            return ToolErrorResponse(self.__class__.__name__, ValueError("old_string 不能为空")).to_str()

        if max_replacements < 1:
            return ToolErrorResponse(self.__class__.__name__, ValueError("max_replacements 必须 >= 1")).to_str()
        if max_replacements > 100:
            max_replacements = 100

        # 2. 路径解析
        source_file_path = Path(file_path)
        resolved_path: Path = self.workspace.path_validator.resolve_path(source_file_path)

        if not resolved_path.is_file():
            return ToolErrorResponse(
                self.__class__.__name__,
                FileNotFoundError(f"文件不存在: {resolved_path}"),
            ).to_str()

        # 3. mtime 校验
        mtime_error = self._validate_mtime(resolved_path)
        if mtime_error:
            return mtime_error

        # 4. 读取文件内容
        old_content = resolved_path.read_text(encoding="utf-8")

        # 5. 查找匹配
        count = 0
        idx = 0
        while count < max_replacements:
            idx = old_content.find(old_string, idx)
            if idx == -1:
                break
            count += 1

            # 上下文校验
            if context_before or context_after:
                ctx_error = self._check_context(old_content, idx, old_string, context_before, context_after, count)
                if ctx_error:
                    return ctx_error

            idx += len(old_string)

        if count == 0:
            return f"No changes made: old_string not found in file.\nFile: {file_path}\nSearching for: '{old_string}'"

        # 6. 执行替换(生成新内容)
        new_content = old_content.replace(old_string, new_string, count)

        # 7. 生成 diff
        rel_path = str(resolved_path.relative_to(self.workspace.root_path))
        diff_content = self._generate_diff(old_content, new_content, rel_path)

        # 8. 记录快照
        from src.core.file_tracker import FileTracker

        old_hash = FileTracker.compute_checksum_from_string(old_content)
        new_hash = FileTracker.compute_checksum_from_string(new_content)
        session_id = self.workspace._current_session_id
        snapshot_id = self.workspace.db.record_file_snapshot(
            rel_path,
            old_hash,
            new_hash,
            diff_content,
            audit_status="PENDING_AUDIT",
            session_id=session_id,
            pending_content=new_content,
        )

        # 9. 返回预览
        return (
            f"[Edit Preview]\n"
            f"File: {rel_path}\n"
            f"Snapshot ID: {snapshot_id}\n"
            f"Replacements: {count}\n"
            f"Diff:\n{diff_content}"
        )

    @staticmethod
    def _check_context(
        content: str,
        match_start: int,
        old_string: str,
        context_before: str,
        context_after: str,
        match_number: int,
    ) -> str | None:
        """校验匹配处的上下文是否与预期一致."""
        if context_before:
            actual_start = max(0, match_start - len(context_before))
            actual_before = content[actual_start:match_start]
            if actual_before != context_before:
                return ToolErrorResponse(
                    "EditTool",
                    ValueError(
                        f"Match {match_number}: context_before mismatch.\n"
                        f"  Expected: '{context_before}'\n"
                        f"  Actual:   '{actual_before}'"
                    ),
                ).to_str()

        if context_after:
            after_start = match_start + len(old_string)
            after_end = min(len(content), after_start + len(context_after))
            actual_after = content[after_start:after_end]
            if actual_after != context_after:
                return ToolErrorResponse(
                    "EditTool",
                    ValueError(
                        f"Match {match_number}: context_after mismatch.\n"
                        f"  Expected: '{context_after}'\n"
                        f"  Actual:   '{actual_after}'"
                    ),
                ).to_str()

        return None
