"""Shell 命令结果标签页 — 查看/复制已执行的 Shell 命令输出."""

from __future__ import annotations

import datetime
from typing import ClassVar

from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Collapsible, Label, Static

from src.core.copy2clip import copy_to_clipboard


class ShellResultTab(Vertical):
    """Shell 命令执行结果标签页.

    展示所有已完成(已批准/已拒绝)的 Shell 命令及其输出,
    支持展开查看详细输出并复制.
    """

    DEFAULT_CSS: ClassVar[str] = """
    ShellResultTab {
        height: 1fr;
        width: 1fr;
        padding: 0 1;
        overflow-y: auto;
    }

    #shell-result-placeholder {
        height: 100%;
        content-align: center middle;
        color: $text-muted;
    }

    #shell-result-empty {
        height: 100%;
        content-align: center middle;
        color: $text-muted;
    }

    #shell-result-header {
        height: auto;
        padding: 1 0;
        text-style: bold;
        color: $text;
    }

    .shell-collapsible {
        height: auto;
        margin-bottom: 1;
    }

    .shell-output-container {
        max-height: 20;
        overflow-y: auto;
        padding: 1;
        background: $surface;
        border: solid $primary;
        margin-bottom: 1;
    }

    .shell-button-row {
        height: auto;
        align: left middle;
        margin-bottom: 1;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._db = None

    def compose(self):
        yield Label("正在加载...", id="shell-result-placeholder")

    def set_database(self, db) -> None:
        """设置数据库引用并刷新."""
        self._db = db
        self.set_timer(0.0, self._refresh)

    def on_mount(self) -> None:
        if self._db is not None:
            self.set_timer(0.1, self._refresh)

    async def _refresh(self) -> None:
        """查询已完成的 Shell 命令并重建 UI."""
        if self._db is None:
            return

        await self.remove_children()

        shells = self._db.get_shell_completed()

        if not shells:
            await self.mount(Label("暂无已执行的 Shell 命令.", id="shell-result-empty"))
            return

        header = Label(f"Shell 命令执行记录 ({len(shells)} 项)", id="shell-result-header")
        await self.mount(header)

        for i, shell in enumerate(shells):
            (
                shell_id,
                command,
                description,
                _ts,
                _sid,
                audit_status,
                output,
                exit_code,
                executed_at,
            ) = shell

            is_approved = audit_status == "APPROVED"
            status_icon = "✓" if is_approved else "✗"
            status_color = "green" if is_approved else "red"

            # Build detailed content
            lines: list[str] = [
                f"[bold]Command:[/bold] $ {command}",
                f"[bold]Status:[/bold] [{status_color}]{status_icon} {audit_status}[/{status_color}]",
            ]
            if description:
                lines.append(f"[bold]Description:[/bold] {description}")
            if exit_code is not None:
                lines.append(f"[bold]Exit Code:[/bold] {exit_code}")
            if executed_at:
                dt_str = datetime.datetime.fromtimestamp(executed_at).strftime("%Y-%m-%d %H:%M:%S")
                lines.append(f"[bold]Executed At:[/bold] {dt_str}")
            if output:
                lines.append(f"\n[bold]Output:[/bold]\n{output}")

            content = "\n".join(lines)

            output_text = Static(content, markup=True)
            output_container = Vertical(output_text, classes="shell-output-container")
            copy_btn = Button("复制输出", id=f"shell_copy-{shell_id}")
            btn_row = Horizontal(copy_btn, classes="shell-button-row")

            # First items expanded by default, rest collapsed
            collapsed = i > 3
            collapsible = Collapsible(
                Vertical(output_container, btn_row),
                title=f"[{status_color}]{status_icon}[/{status_color}] Shell #{shell_id}: {command.strip()[:60]}{'...' if len(command.strip()) > 60 else ''}",
                classes="shell-collapsible",
                collapsed=collapsed,
            )
            await self.mount(collapsible)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """处理复制按钮点击."""
        button_id = event.button.id or ""
        if not button_id.startswith("shell_copy-"):
            return

        try:
            shell_id = int(button_id.split("-", 1)[1])
        except ValueError, IndexError:
            return

        if self._db is None:
            return

        shells = self._db.get_shell_completed()
        for shell in shells:
            if shell[0] == shell_id:
                output = shell[6] or "(空输出)"
                copy_to_clipboard(output)
                self.notify("输出已复制到剪贴板", timeout=3)
                return

        self.notify("未找到对应记录", severity="error", timeout=3)
