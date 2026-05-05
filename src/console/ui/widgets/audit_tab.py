"""审核标签页 — 待审核与已审核历史双标签页视图."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import ClassVar

from rich.markup import escape
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Collapsible, Label, Static, TabbedContent, TabPane


class ConfirmScreen(Screen[bool]):
    """模态确认对话框."""

    DEFAULT_CSS = """
    ConfirmScreen {
        align: center middle;
    }

    #confirm-dialog {
        width: 50;
        height: auto;
        padding: 2 3;
        background: $surface;
        border: thick $primary;
    }

    #confirm-message {
        text-align: center;
        margin-bottom: 1;
    }

    #confirm-buttons {
        height: auto;
        align: center middle;
    }

    #confirm-buttons Button {
        margin: 0 1;
    }
    """

    def __init__(self, message: str) -> None:
        super().__init__()
        self._message = message

    def compose(self):
        with Vertical(id="confirm-dialog"):
            yield Static(self._message, id="confirm-message")
            with Horizontal(id="confirm-buttons"):
                yield Button("确认", variant="primary", id="confirm-yes")
                yield Button("取消", variant="default", id="confirm-no")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm-yes":
            self.dismiss(True)
        else:
            self.dismiss(False)

    def key_escape(self) -> None:
        self.dismiss(False)


class AuditTab(Vertical):
    """审核标签页.

    包含两个子标签页:
    - 待审核的更改: 显示所有 PENDING_AUDIT 的文件快照
    - 已审核历史: 显示所有已批准/拒绝的审核记录
    """

    DEFAULT_CSS: ClassVar[str] = """
    AuditTab {
        height: 1fr;
        width: 1fr;
        padding: 0 1;
        overflow-y: auto;
    }

    AuditTab TabbedContent {
        height: 1fr;
    }

    /* ---- Pending tab ---- */

    #pending-header {
        height: auto;
        padding: 1 0;
        text-style: bold;
        color: $text;
    }

    #pending-empty {
        height: 100%;
        content-align: center middle;
        color: $text-muted;
    }

    #audit-result-log {
        height: auto;
        max-height: 6;
        overflow-y: auto;
        border: solid $accent;
        padding: 0 1;
        margin-bottom: 1;
    }

    .audit-collapsible {
        height: auto;
        margin-bottom: 1;
    }

    .audit-diff {
        height: auto;
        max-height: 15;
        overflow-y: auto;
        padding: 1;
        background: $surface;
        border: solid $primary;
        margin-bottom: 1;
    }

    .audit-buttons {
        height: auto;
        align: left middle;
        margin-bottom: 1;
    }

    .audit-approve {
        margin-right: 1;
    }

    .audit-reject {
        margin-right: 1;
    }

    /* ---- Batch buttons ---- */

    .batch-buttons {
        height: auto;
        align: left middle;
        margin-bottom: 1;
        padding: 1 0;
    }

    .batch-buttons Button {
        margin-right: 1;
    }

    .file-batch-buttons {
        height: auto;
        align: left middle;
        margin-bottom: 1;
    }

    .file-batch-buttons Button {
        margin-right: 1;
    }

    /* ---- History tab ---- */

    .filter-buttons {
        height: auto;
        align: left middle;
        margin-bottom: 1;
        padding: 1 0;
    }

    .filter-buttons Button {
        margin-right: 1;
    }

    #history-header {
        height: auto;
        padding: 1 0;
        text-style: bold;
        color: $text;
    }

    #history-empty {
        height: 100%;
        content-align: center middle;
        color: $text-muted;
    }

    .history-entry {
        height: auto;
        margin-bottom: 1;
    }

    .history-status {
        height: auto;
        padding: 0 1;
        margin-bottom: 1;
    }

    .history-status-approved {
        color: $success;
        text-style: bold;
    }

    .history-status-rejected {
        color: $error;
        text-style: bold;
    }

    .history-diff {
        height: auto;
        max-height: 12;
        overflow-y: auto;
        padding: 1;
        background: $surface;
        border: solid $primary;
        margin-bottom: 1;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._committer = None
        # Map: file_index -> (snapshot_ids, file_path)
        self._file_batch_map: dict[int, tuple[list[int], str]] = {}
        self._history_filter: str = "all"

    def compose(self):
        with TabbedContent():
            with TabPane("待审核的更改", id="tab-pending"), Vertical():
                yield Horizontal(
                    Button("同意全部更改", variant="primary", id="batch-approve-all"),
                    Button("拒绝全部更改", variant="error", id="batch-reject-all"),
                    classes="batch-buttons",
                )
                yield Vertical(id="audit-result-log")
                yield Label("待审核更改", id="pending-header")
                yield Vertical(id="pending-list")
            with TabPane("已审核历史", id="tab-history"), Vertical():
                yield Horizontal(
                    Button("全部", id="history-filter-all"),
                    Button("已批准", id="history-filter-approved"),
                    Button("已拒绝", id="history-filter-rejected"),
                    classes="filter-buttons",
                )
                yield Label("已审核历史", id="history-header")
                yield Vertical(id="history-list")

    # -- Lifecycle --

    def set_committer(self, committer) -> None:
        """设置审核提交模块并刷新列表."""
        self._committer = committer
        self.set_timer(0.0, self._refresh)

    def on_mount(self) -> None:
        """控件挂载后刷新."""
        if self._committer is not None:
            self.set_timer(0.1, self._refresh)

    # -- Tab switching --

    async def _refresh(self) -> None:
        """外部刷新入口 — 刷新待审核标签页."""
        await self._refresh_pending()

    async def on_tabbed_content_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        """内标签页切换时刷新对应内容."""
        if self._committer is None:
            return
        if event.pane.id == "tab-history":
            await self._refresh_history()
        elif event.pane.id == "tab-pending":
            await self._refresh_pending()

    # -- Pending tab --

    async def _refresh_pending(self) -> None:
        """查询待审核列表并重建 UI."""
        if self._committer is None:
            return

        pending_list = self.query_one("#pending-list", Vertical)
        await pending_list.remove_children()

        pending = self._committer.workspace.db.get_snapshots_by_audit_status("PENDING_AUDIT")

        if not pending:
            await self.query_one("#pending-header", Label).update("没有待审核的更改.")
            return

        grouped: defaultdict[str, list[tuple]] = defaultdict(list)
        for snap in pending:
            grouped[snap[1]].append(snap)

        total_count = sum(len(snaps) for snaps in grouped.values())
        await self.query_one("#pending-header", Label).update(f"待审核更改 ({total_count} 项)")

        self._file_batch_map.clear()
        file_index = 0

        for file_path in sorted(grouped):
            snaps = grouped[file_path]
            snap_ids = [snap[0] for snap in snaps]
            file_index += 1
            self._file_batch_map[file_index] = (snap_ids, file_path)

            all_snap_widgets: list[Static | Horizontal] = []

            # File-level batch buttons
            file_batch_row = Horizontal(
                Button("同意文件中所有更改", variant="primary", id=f"fapp-{file_index}", classes="audit-approve"),
                Button("拒绝文件中所有更改", variant="error", id=f"frej-{file_index}", classes="audit-reject"),
                classes="file-batch-buttons",
            )
            all_snap_widgets.append(file_batch_row)

            for snap in snaps:
                snap_id = snap[0]
                diff_content = snap[4] or "(空 diff)"

                diff_container = Vertical(Static(diff_content, markup=False), classes="audit-diff")
                btn_row = Horizontal(
                    Button("批准", variant="primary", id=f"approve-{snap_id}", classes="audit-approve"),
                    Button("拒绝", variant="error", id=f"reject-{snap_id}", classes="audit-reject"),
                    classes="audit-buttons",
                )
                all_snap_widgets.append(diff_container)
                all_snap_widgets.append(btn_row)

            content_widgets = Vertical(*all_snap_widgets)

            collapsible = Collapsible(
                content_widgets,
                title=f"{file_path} ({len(snaps)} 次更改)",
                classes="audit-collapsible",
            )
            await pending_list.mount(collapsible)

    # -- History tab --

    async def _refresh_history(self) -> None:
        """查询已审核历史并重建 UI."""
        if self._committer is None:
            return

        history_list = self.query_one("#history-list", Vertical)
        await history_list.remove_children()

        db = self._committer.workspace.db
        if self._history_filter == "approved":
            history = db.get_snapshots_by_audit_status("APPROVED")
        elif self._history_filter == "rejected":
            history = db.get_snapshots_by_audit_status("REJECTED")
        else:
            approved = db.get_snapshots_by_audit_status("APPROVED")
            rejected = db.get_snapshots_by_audit_status("REJECTED")
            history = approved + rejected
            history.sort(key=lambda x: x[5], reverse=True)

        if not history:
            await self.query_one("#history-header", Label).update("没有已审核的记录.")
            return

        filter_label = {"all": "全部", "approved": "已批准", "rejected": "已拒绝"}
        await self.query_one("#history-header", Label).update(
            f"已审核历史 ({filter_label[self._history_filter]}) — {len(history)} 项"
        )

        grouped: defaultdict[str, list[tuple]] = defaultdict(list)
        for snap in history:
            grouped[snap[1]].append(snap)

        for file_path in sorted(grouped):
            snaps = grouped[file_path]
            entry_widgets: list[Vertical] = []

            for snap in snaps:
                diff_content = snap[4] or "(空 diff)"
                timestamp = snap[5]
                audit_status = snap[7]

                time_str = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
                status_text = "已批准" if audit_status == "APPROVED" else "已拒绝"
                status_class = "history-status-approved" if audit_status == "APPROVED" else "history-status-rejected"

                entry_widgets.append(
                    Vertical(
                        Static(
                            f"[{status_class}]{status_text}[/{status_class}]  —  审核时间: {time_str}",
                            classes="history-status",
                        ),
                        Static(diff_content, markup=False, classes="history-diff"),
                        classes="history-entry",
                    )
                )

            content_widgets = Vertical(*entry_widgets)
            collapsible = Collapsible(
                content_widgets,
                title=f"{file_path} ({len(snaps)} 项)",
                classes="audit-collapsible",
            )
            await history_list.mount(collapsible)

    # -- Result logging --

    async def _append_result(self, message: str, color: str = "green") -> None:
        """追加一条结果消息到结果日志."""
        try:
            log = self.query_one("#audit-result-log", Vertical)
            escaped = escape(message)
            await log.mount(Static(f"[{color}]{escaped}[/{color}]"))
        except Exception:
            pass

    # -- Button dispatching --

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """处理所有按钮点击."""
        if self._committer is None:
            return

        button_id = event.button.id or ""

        # History filter
        if button_id == "history-filter-all":
            self._history_filter = "all"
            await self._refresh_history()
            return
        if button_id == "history-filter-approved":
            self._history_filter = "approved"
            await self._refresh_history()
            return
        if button_id == "history-filter-rejected":
            self._history_filter = "rejected"
            await self._refresh_history()
            return

        # Global batch
        if button_id == "batch-approve-all":
            await self._batch_all(approved=True)
            return
        if button_id == "batch-reject-all":
            await self._batch_all(approved=False)
            return

        # Parse action-suffix
        parts = button_id.split("-", 1)
        if len(parts) != 2:
            return
        action, suffix = parts

        # File-level batch
        if action == "fapp":
            idx = int(suffix)
            data = self._file_batch_map.get(idx)
            if data:
                await self._batch_file(data[0], data[1], approved=True)
            return
        if action == "frej":
            idx = int(suffix)
            data = self._file_batch_map.get(idx)
            if data:
                await self._batch_file(data[0], data[1], approved=False)
            return

        # Individual approve/reject
        if action in ("approve", "reject"):
            try:
                snap_id = int(suffix)
            except ValueError:
                return
            approved = action == "approve"
            result = self._committer.commit(snap_id, approved)
            color = "green" if "已批准" in result or "已拒绝" in result else "red"
            await self._append_result(result, color)
            await self._refresh()
            return

    # -- Batch operations --

    async def _batch_all(self, approved: bool) -> None:
        """批量处理所有待审核更改."""
        action_text = "同意" if approved else "拒绝"
        confirmed = await self.app.push_screen(ConfirmScreen(f"确定{action_text}所有待审核的更改?"))
        if not confirmed:
            return

        pending = self._committer.workspace.db.get_snapshots_by_audit_status("PENDING_AUDIT")
        snap_ids = [snap[0] for snap in pending]
        if not snap_ids:
            await self._append_result("没有待审核的更改.", "red")
            return

        results = self._committer.batch_commit(snap_ids, approved)
        success = sum(1 for _, r in results if "已批准" in r or "已拒绝" in r)
        color = "green" if success > 0 else "red"
        await self._append_result(
            f"批量{action_text}: {success} 项成功处理, {len(results) - success} 项失败",
            color,
        )
        await self._refresh()

    async def _batch_file(self, snap_ids: list[int], file_path: str, approved: bool) -> None:
        """批量处理单个文件中的所有待审核更改."""
        action_text = "同意" if approved else "拒绝"
        confirmed = await self.app.push_screen(ConfirmScreen(f"确定{action_text}{file_path}中的所有更改?"))
        if not confirmed:
            return

        results = self._committer.batch_commit(snap_ids, approved)
        success = sum(1 for _, r in results if "已批准" in r or "已拒绝" in r)
        color = "green" if success > 0 else "red"
        await self._append_result(
            f"{file_path}: 批量{action_text} — {success} 项成功, {len(results) - success} 项失败",
            color,
        )
        await self._refresh()
