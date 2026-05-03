from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from rich.panel import Panel
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Footer, Label, TextArea

from src.console.handlers.command_handler import CommandHandler
from src.console.handlers.tool_handler import ToolHandler
from src.console.ui.tui_console import TuiConsole
from src.core.input_parser import parse_input
from src.core.paste_cache import PasteReference
from src.core.paste_window import show_paste_window
from src.utils.generate_help_text import generate_help_text
from src.utils.string_snapshot import truncate_for_display

if TYPE_CHECKING:
    from src.console.result_manager import ResultManager
    from src.core.tool_registry import ToolRegistry
    from src.workspace.workspace import Workspace


# ---------------------------------------------------------------------------
# Textual 应用
# ---------------------------------------------------------------------------


class REPL(App):
    """ManualAid REPL —— 基于 Textual 的终端应用"""

    CONSOLE_TITLE = "ManualAid"

    # 内联 CSS
    CSS = """
    /* 标题栏:水平容器,整体垂直居中 */
    #title-bar {
        height: 3;
        dock: top;
        border-bottom: solid $primary;
    }

    #title-bar > Horizontal {
        height: 100%;
        align: center middle;
    }

    #title-left {
        width: 20%;
        content-align: right middle;
        text-style: bold;
        color: $success;
        margin-right: 1;
    }

    #title-version {
        width: 20%;
        content-align: left middle;
        color: $text-muted;
        text-style: italic;
        text-opacity: 60%;
        margin-left: 1;
    }

    #title-right {
        width: 60%;
        content-align: center middle;
        color: $text-muted;
    }

    /* 输入区域:固定在底部 */
    #input-area {
        dock: bottom;
        height: auto;
        min-height: 3;
        max-height: 12;
        padding: 1;
        border-top: solid $primary;
    }

    #input-area > Horizontal {
        height: auto;
    }

    /* 余多行输入框占据剩宽度 */
    #input-field {
        width: 1fr;
        min-height: 2;
        max-height: 10;
        border: wide $accent;
        background: $boost;
    }

    #input-container {
        width: 1fr;
    }

    #button-area {
        width: auto;
        margin-left: 1;
        margin-right: 0;
        padding: 1;
    }

    /* 提交按钮 */
    #submit-btn {
        width: 1;
        min-height: 1;
    }

    #big-paste-btn {
        width: 1;
        min-height: 1;
    }

    /* 隐藏 footer 中的 palette */
    Footer > #palette {
        display: none;
    }
    """

    # 按键绑定
    BINDINGS: ClassVar[list] = [
        Binding("ctrl+q", "quit_confirm", "退出", show=True),
        Binding("ctrl+j", "submit_text", "提交", show=True),
        Binding("alt+v", "paste_big_text", "粘贴大文本", show=True),
    ]

    def __init__(
        self,
        workspace: Workspace,
        tool_registry: ToolRegistry,
        result_manager: ResultManager,
    ):
        super().__init__()
        self.tui_console: TuiConsole | None = None
        self.workspace = workspace
        self.tool_registry = tool_registry
        self.result_manager = result_manager

        # handler 在 on_mount 中创建(此时控件树已就绪)
        self.command_handler: CommandHandler | None = None
        self.tool_handler: ToolHandler | None = None

        self.paste_reference: PasteReference = PasteReference()

        # 多行输入缓冲区(用于 func_call 跨行输入)
        self._multiline_buffer: list[str] = []

    # -- 构建控件树 ---------------------------------------------------------

    def compose(self) -> ComposeResult:
        """构建控件树"""

        # 标题栏:左侧名称 + 中间工作区路径 + 右侧版本号
        with Horizontal(id="title-bar"), Horizontal():
            yield Label(self.CONSOLE_TITLE, id="title-left")
            from src.constants import __version__

            yield Label(f"v{__version__}", id="title-version")
            yield Label("工作区", id="title-right")

        # 输出区域: 使用新的 TuiConsole 组件
        yield TuiConsole()

        # 输入区域:水平布局,多行输入框 + 提交按钮
        with Horizontal(id="input-area"):
            with Vertical(id="input-container"):
                yield Label(
                    "输入命令或 [yellow]<func_call>[/yellow] 标签,Ctrl+J 提交",
                    id="input-label",
                )
                yield TextArea(
                    "",
                    language="python",
                    id="input-field",
                )
            with Vertical(id="button-area"):
                yield Button("提交", id="submit-btn", variant="primary")
                yield Button("大文本粘贴", id="big-paste-btn", variant="primary")

        yield Footer(show_command_palette=False)

    # -- 生命周期 -----------------------------------------------------------

    def on_mount(self) -> None:
        """控件挂载后初始化 handler 并打印欢迎横幅"""
        tui_console = self.query_one(TuiConsole)
        self.tui_console = tui_console
        self.result_manager.console = tui_console

        # 更新标题栏右侧显示实际工作区路径
        title_right = self.query_one("#title-right", Label)
        title_right.update(f"工作区: {self.workspace.root_path}")

        # 创建审核提交模块并注入审核标签页
        from src.core.audit_committer import AuditCommitter

        audit_committer = AuditCommitter(self.workspace)
        tui_console.audit_tab.set_committer(audit_committer)

        # 注入统计标签页
        tui_console.stats_tab.set_database(
            self.workspace.db,
            getattr(self.tool_registry, "_current_session_id", None),
        )

        # 创建 command handler
        self.command_handler = CommandHandler(
            self.workspace,
            self.tool_registry,
            self.result_manager,
            tui_console,  # type: ignore[arg-type]
            self,
        )

        # 创建 tool handler
        self.tool_handler = ToolHandler(
            self.tool_registry,
            self.result_manager,
            tui_console,  # type: ignore[arg-type]
        )

        self._print_welcome()

        # 自动聚焦输入框
        self.query_one("#input-field", TextArea).focus()

    # -- 输入处理 -----------------------------------------------------------

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """处理提交按钮点击"""
        if event.button.id == "submit-btn":
            self._do_submit()
        if event.button.id == "big-paste-btn":
            self.action_paste_big_text()

    def _do_submit(self) -> None:
        """从 TextArea 中取出文本并提交"""
        text_area = self.query_one("#input-field", TextArea)
        text = text_area.text.rstrip("\n")

        # 清空输入框
        text_area.clear()

        self.tui_console.print(f"> {truncate_for_display(text)}")

        if not text.strip():
            return

        text = self.paste_reference.expand(text).replace("&quot;", '"')
        self.paste_reference.clear()

        # 单行模式下直接分发
        self._dispatch(text)

    def action_paste_big_text(self):
        def on_paste_result(text: str):
            if text:
                self.call_from_thread(self._insert_paste_text, text)

        show_paste_window(callback=on_paste_result)

    def _insert_paste_text(self, text: str) -> None:
        """在主线程中插入粘贴的文本"""
        text_area = self.query_one("#input-field", TextArea)
        if self.paste_reference.should_collapse(text):
            text = self.paste_reference.collapsed(text)
        text_area.insert(text)

    def action_submit_text(self) -> None:
        """Ctrl+Enter 提交文本"""
        self._do_submit()

    def _dispatch(self, user_input: str) -> None:
        """解析并执行一条完整的用户输入"""
        assert self.command_handler is not None
        assert self.tool_handler is not None
        assert self.tui_console is not None

        warns: list[str] = []
        parsed = parse_input(user_input, self.command_handler.registry, warns)

        try:
            if parsed.is_command:
                self.command_handler.handle(parsed)
            elif parsed.is_func:
                self.tool_handler.handle(parsed)
            else:
                self.tui_console.print(
                    Panel(
                        f"输入内容既不是工具也不是函数: {truncate_for_display(user_input)}",
                        title="输入解析错误",
                    )
                )
        except Exception as e:
            warns.append(f"分发输入后在执行时出现错误: {e}")

        if len(warns) > 0:
            joined_warns = "\n".join(warns)
            self.tui_console.print(Panel(f"[yellow]{joined_warns}[/yellow]", title="输入分发警告"))

    def action_quit_confirm(self) -> None:
        """退出应用"""
        session_id = getattr(self.tool_registry, "_current_session_id", None)
        if session_id is not None and hasattr(self.workspace, "db"):
            self.workspace.db.close_session(session_id)
        if self.tui_console:
            self.tui_console.print("[bold]再见![/bold]")
        self.exit()

    def _print_welcome(self) -> None:
        """在输出区域打印欢迎横幅"""
        assert self.tui_console is not None
        assert self.command_handler is not None

        self.tui_console.print(f"[bold green]{self.CONSOLE_TITLE}[/bold green]")
        self.tui_console.print(f"[dim]工作区: {self.workspace.root_path}[/dim]")
        self.tui_console.print("")
        self.tui_console.print(generate_help_text(self.command_handler.registry.list_commands()))
        self.tui_console.print("[dim]输入 /help 查看命令,Ctrl+Q 退出[/dim]")
        self.tui_console.print("")
