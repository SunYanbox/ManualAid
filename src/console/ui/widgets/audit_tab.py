"""审核标签页 — 显示待审核的文件快照."""

from __future__ import annotations

from collections import defaultdict
from typing import ClassVar

from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Collapsible, Label, Static


class AuditTab(Vertical):
    """审核标签页.

    显示所有 PENDING_AUDIT 的文件快照，
    每个文件作为一个可折叠块，含 diff 内容和批准/拒绝按钮。
    """

    DEFAULT_CSS: ClassVar[str] = """
    AuditTab {
        height: 1fr;
        width: 1fr;
        padding: 0 1;
    }

    #audit-placeholder {
        height: 100%;
        content-align: center middle;
        color: $text-muted;
    }

    #audit-empty {
        height: 100%;
        content-align: center middle;
        color: $text-muted;
    }

    #audit-header {
        height: auto;
        padding: 1 0;
        text-style: bold;
        color: $text;
    }

    .audit-collapsible {
        height: auto;
        margin-bottom: 1;
    }

    .audit-diff {
        height: auto;
        padding: 1;
        background: $surface;
        border: solid $primary;
        margin-bottom: 1;
        font-family: monospace;
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

    #audit-result-log {
        height: auto;
        max-height: 6;
        overflow-y: auto;
        border: solid $accent;
        padding: 0 1;
        margin-bottom: 1;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._committer = None

    def compose(self):
        yield Label("正在加载审核列表...", id="audit-placeholder")

    def set_committer(self, committer) -> None:
        """设置审核提交模块并刷新列表."""
        self._committer = committer
        self._refresh()

    def on_mount(self) -> None:
        """控件挂载后刷新."""
        if self._committer is not None:
            # 延迟一下让 UI 就绪
            self.set_timer(0.1, self._refresh)

    def _refresh(self) -> None:
        """查询待审核列表并重建 UI."""
        if self._committer is None:
            return

        self.remove_children()

        pending = self._committer.workspace.db.get_snapshots_by_audit_status("PENDING_AUDIT")

        if not pending:
            self.mount(Label("没有待审核的更改。", id="audit-empty"))
            return

        # Group by file_path
        grouped: defaultdict[str, list[tuple]] = defaultdict(list)
        for snap in pending:
            grouped[snap[1]].append(snap)

        # Result area for showing commit results
        result_log = Vertical(id="audit-result-log")
        self.mount(result_log)

        header = Label(
            f"待审核更改 ({sum(len(snaps) for snaps in grouped.values())} 项)",
            id="audit-header",
        )
        self.mount(header)

        for file_path in sorted(grouped):
            snaps = grouped[file_path]
            # Use first snapshot's id for the collapsible key
            content_widgets = Vertical()
            for snap in snaps:
                snap_id = snap[0]
                diff_content = snap[4] or "(空 diff)"

                diff_static = Static(diff_content, classes="audit-diff")
                btn_row = Horizontal(
                    Button("批准", variant="primary", id=f"approve-{snap_id}", classes="audit-approve"),
                    Button("拒绝", variant="error", id=f"reject-{snap_id}", classes="audit-reject"),
                    classes="audit-buttons",
                )
                content_widgets.mount(diff_static)
                content_widgets.mount(btn_row)

            collapsible = Collapsible(
                content_widgets,
                title=f"{file_path} ({len(snaps)} 次更改)",
                classes="audit-collapsible",
            )
            # Collapse excess items initially — keep first 3 expanded
            if len(self.children) > 6:  # header + result_log + 3 expanded
                collapsible.collapsed = True
            self.mount(collapsible)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """处理批准/拒绝按钮点击."""
        if self._committer is None:
            return

        button_id = event.button.id or ""

        parts = button_id.split("-", 1)
        if len(parts) != 2:
            return

        action, snap_id_str = parts
        try:
            snapshot_id = int(snap_id_str)
        except ValueError:
            return

        if action == "approve":
            result = self._committer.commit(snapshot_id, approved=True)
        elif action == "reject":
            result = self._committer.commit(snapshot_id, approved=False)
        else:
            return

        # Show result in the result log
        try:
            log = self.query_one("#audit-result-log", Vertical)

            color = "green" if "已批准" in result or "已拒绝" in result else "red"
            log.mount(Static(f"[{color}]{result}[/{color}]"))
        except Exception:
            pass

        # Refresh the list
        self._refresh()
