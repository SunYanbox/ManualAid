"""审核标签页 — 显示待审核的文件快照."""

from __future__ import annotations

from collections import defaultdict
from typing import ClassVar

from rich.markup import escape
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Collapsible, Label, Static


class AuditTab(Vertical):
    """审核标签页.

    显示所有 PENDING_AUDIT 的文件快照,
    每个文件作为一个可折叠块,含 diff 内容和批准/拒绝按钮.
    """

    DEFAULT_CSS: ClassVar[str] = """
    AuditTab {
        height: 1fr;
        width: 1fr;
        padding: 0 1;
        overflow-y: auto;
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

    #audit-result-log {
        height: auto;
        max-height: 6;
        overflow-y: auto;
        border: solid $accent;
        padding: 0 1;
        margin-bottom: 1;
    }

    .audit-section-label {
        height: auto;
        padding: 0 0 0 0;
        text-style: bold;
        color: $text;
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
        self.set_timer(0.0, self._refresh)

    def on_mount(self) -> None:
        """控件挂载后刷新."""
        if self._committer is not None:
            # 延迟一下让 UI 就绪
            self.set_timer(0.1, self._refresh)

    async def _refresh(self) -> None:
        """查询待审核列表并重建 UI."""
        if self._committer is None:
            return

        await self.remove_children()

        # Result area for showing commit results
        result_log = Vertical(id="audit-result-log")
        await self.mount(result_log)

        pending_files = self._committer.workspace.db.get_snapshots_by_audit_status("PENDING_AUDIT")
        pending_shells = self._committer.workspace.db.get_shell_pending_audits()

        total_items = len(pending_files) + len(pending_shells)

        if total_items == 0:
            await self.mount(Label("没有待审核的更改.", id="audit-empty"))
            return

        # Group file snapshots by file_path
        file_grouped: defaultdict[str, list[tuple]] = defaultdict(list)
        for snap in pending_files:
            file_grouped[snap[1]].append(snap)

        header = Label(
            f"待审核更改 ({total_items} 项)",
            id="audit-header",
        )
        await self.mount(header)

        # Render pending shell commands first
        if pending_shells:
            shell_children: list[Label | Collapsible] = [Label("Shell 命令:", classes="audit-section-label")]
            for shell in pending_shells:
                shell_id, command, description, _ts, _sid, _status = shell
                preview = f"$ {command}"
                if description:
                    preview += f"\n  # {description}"

                cmd_display = Static(preview, markup=False, classes="audit-diff")
                btn_row = Horizontal(
                    Button("批准", variant="primary", id=f"shell_approve-{shell_id}", classes="audit-approve"),
                    Button("拒绝", variant="error", id=f"shell_reject-{shell_id}", classes="audit-reject"),
                    classes="audit-buttons",
                )
                collapsible = Collapsible(
                    Vertical(cmd_display, btn_row),
                    title=f"Shell #{shell_id}: {command.strip()[:60]}{'...' if len(command.strip()) > 60 else ''}",
                    classes="audit-collapsible",
                )
                shell_children.append(collapsible)
            await self.mount(Vertical(*shell_children))

        # Render file snapshot changes
        if pending_files:
            for file_path in sorted(file_grouped):
                snaps = file_grouped[file_path]
                all_snap_widgets: list[Static | Horizontal] = []
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
                if len(self.children) > 6:
                    collapsible.collapsed = True
                await self.mount(collapsible)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """处理批准/拒绝按钮点击."""
        if self._committer is None:
            return

        button_id = event.button.id or ""

        parts = button_id.split("-", 1)
        if len(parts) != 2:
            return

        action, id_str = parts
        try:
            item_id = int(id_str)
        except ValueError:
            return

        if action == "approve":
            result = self._committer.commit(item_id, approved=True)
        elif action == "reject":
            result = self._committer.commit(item_id, approved=False)
        elif action == "shell_approve":
            result = self._committer.commit_shell(item_id, approved=True)
        elif action == "shell_reject":
            result = self._committer.commit_shell(item_id, approved=False)
        else:
            return

        # Show result in the result log
        try:
            log = self.query_one("#audit-result-log", Vertical)

            color = "green" if "已批准" in result or "已拒绝" in result else "red"
            escaped = escape(result)
            await log.mount(Static(f"[{color}]{escaped}[/{color}]"))
        except Exception:
            pass

        # Refresh the list
        await self._refresh()
