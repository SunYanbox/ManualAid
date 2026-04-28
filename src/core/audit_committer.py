from pathlib import Path

from src.workspace.workspace import Workspace


class AuditCommitter:
    """审核提交模块 — 处理待审核的写入/编辑操作.

    不是 LLM 工具，供审核 UI 标签页调用。
    新文件使用 create_file_with_parents() 创建并写入，
    已有文件进行 mtime 校验后通过 write_text() 写入。
    """

    def __init__(self, workspace: Workspace):
        self.workspace = workspace

    def commit(self, snapshot_id: int, approved: bool = True) -> str:
        """执行审核结果。

        Args:
            snapshot_id: 文件快照 ID
            approved: True=批准写入, False=拒绝

        Returns:
            操作结果消息
        """
        db = self.workspace.db

        # 1. 获取快照
        snap = db.get_snapshot_by_id(snapshot_id)
        if snap is None:
            return f"快照不存在: {snapshot_id}"

        (
            _snap_id,
            file_path,
            _old_hash,
            _new_hash,
            _diff_content,
            _timestamp,
            _session_id,
            audit_status,
            pending_content,
        ) = snap

        # 2. 检查状态
        if audit_status != "PENDING_AUDIT":
            return f"快照已处理 (当前状态: {audit_status})"

        if not approved:
            db.update_snapshot_audit(snapshot_id, "REJECTED")
            return f"已拒绝 (snapshot_id={snapshot_id})"

        # 3. 批准 — 执行写入
        try:
            resolved = self.workspace.path_validator.resolve_path(Path(file_path))

            if not resolved.exists():
                # 全新文件 — 使用 create_file_with_parents
                self.workspace.path_validator.create_file_with_parents(resolved, pending_content)
            else:
                # 已有文件 — mtime 校验后 write_text
                rel_path = str(resolved.relative_to(self.workspace.root_path))
                record = db.get_file_read_record(rel_path)
                if record is not None:
                    stored_mtime = record[2]
                    current_mtime = resolved.stat().st_mtime
                    if abs(current_mtime - stored_mtime) > 0.001:
                        return f"ERROR: 文件已被外部修改，审核终止: {rel_path}。请重新读取后再批准。"
                resolved.write_text(pending_content, encoding="utf-8")

            # 4. 更新 file_read_records
            from src.core.file_tracker import FileTracker

            rel_path = str(resolved.relative_to(self.workspace.root_path))
            new_meta = FileTracker.get_file_meta(resolved)
            if new_meta:
                db.record_file_read(rel_path, new_meta["mtime"], new_meta["size"], new_meta["checksum"])

            # 5. 更新审计状态
            db.update_snapshot_audit(snapshot_id, "APPROVED")

            return f"已批准并写入文件 (snapshot_id={snapshot_id})"

        except Exception as e:
            return f"写入失败: {e.__class__.__name__}({e})"
