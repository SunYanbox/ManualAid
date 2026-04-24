"""REPL 循环实现 -- 基于 Textual 的 TUI"""

import os
import platform
from typing import TYPE_CHECKING, ClassVar

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Footer, Label, RichLog, TextArea

from src.console.commands.base import Command, CommandContext, CommandResult
from src.console.commands.registry import CommandRegistry
from src.console.handlers.command_handler import CommandHandler
from src.console.handlers.tool_handler import ToolHandler
from src.console.input_parser import parse_input
from src.core.paste_cache import PasteReference
from src.core.paste_window import show_paste_window

if TYPE_CHECKING:
    from src.console.result_manager import ResultManager
    from src.core.tool_registry import ToolRegistry
    from src.workspace.workspace import Workspace


def _generate_help_text(cmds: list[Command]) -> str:
    """生成帮助文本,返回 Rich markup 字符串"""
    lines: list[str] = [
        "[bold magenta]可用命令[/bold magenta]\n",
        "  [cyan]名称[/cyan]          [cyan]别名[/cyan]              [cyan]描述[/cyan]",
        "  " + chr(9472) * 70,
    ]
    for cmd in cmds:
        alias_str = " | ".join(f"[italic magenta]{a}[/italic magenta]" for a in cmd.aliases)
        lines.append(f"  [cyan]{cmd.name:<16}[/cyan] {alias_str:<24} [grey85]{cmd.description}[/grey85]")
    lines.append("")
    lines.append("[bold cyan]工具:[/bold cyan]")
    lines.append("[dim]使用 XML 标签调用工具,格式如下:[/dim]")
    lines.append(
        '[yellow bold]<func_call>{"func_name": "tool_name", "args": [...], "kwargs": {...}}</func_call>[/yellow bold]'
    )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 命令(在 REPL 初始化时注册)
# ---------------------------------------------------------------------------


class HelpCommand(Command):
    """显示帮助信息"""

    def __init__(self, cmd_registry: CommandRegistry):
        super().__init__()
        self.name = "help"
        self.aliases = ["/help", "/h", "/?"]
        self.description = "显示帮助信息"
        self.usage = "/help 或 /h 或 /?"
        self.cmd_registry = cmd_registry

    def execute(self, context: CommandContext) -> CommandResult:
        context.console.print(_generate_help_text(self.cmd_registry.list_commands()))
        return CommandResult(success=True)


class ClsCommand(Command):
    """Cls command"""

    def __init__(self, command_registry: CommandRegistry):
        super().__init__()
        self.name = "cls"
        self.aliases = ["/cls"]
        self.description = "Clear the console"
        self.usage = "/cls"
        self._command_registry = command_registry

    def execute(self, context: CommandContext) -> CommandResult:
        # Windows
        if platform.system() == "Windows":
            os.system("cls")
        # Linux/macOS
        else:
            os.system("clear")
        context.console.clear()
        if context.app:
            context.app.refresh()
            context.console.print(_generate_help_text(self._command_registry.list_commands()))
        return CommandResult(success=True)


# ---------------------------------------------------------------------------
# 适配器:将 Textual RichLog 伪装成 rich.console.Console
# 让现有命令中 context.console.print / clear 调用无需立即改动
# ---------------------------------------------------------------------------


class _TuiConsole:
    """适配器,将对 rich.console.Console 的调用转发到 Textual RichLog"""

    def __init__(self, log: RichLog) -> None:
        self._log = log

    def print(self, *args, **kwargs) -> None:
        """将内容写入 RichLog 控件"""
        for arg in args:
            if isinstance(arg, str):
                self._log.write(arg)
            else:
                self._log.write(arg)

    def clear(self) -> None:
        """清空输出区域"""
        self._log.clear()


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
        width: 40%;
        content-align: center middle;
        text-style: bold;
        color: $success;
    }

    #title-right {
        width: 60%;
        content-align: center middle;
        color: $text-muted;
    }

    /* 输出区域占据剩余空间 */
    #output {
        height: 1fr;
        border: none;
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
        workspace: "Workspace",
        tool_registry: "ToolRegistry",
        result_manager: "ResultManager",
    ):
        super().__init__()
        self.workspace = workspace
        self.tool_registry = tool_registry
        self.result_manager = result_manager

        # handler 在 on_mount 中创建(此时控件树已就绪)
        self.command_handler: CommandHandler | None = None
        self.tool_handler: ToolHandler | None = None

        self.paste_refence: PasteReference = PasteReference()

        # 多行输入缓冲区(用于 func_call 跨行输入)
        self._multiline_buffer: list[str] = []

    # -- 构建控件树 ---------------------------------------------------------

    def compose(self) -> ComposeResult:
        """构建控件树"""

        # 标题栏:左侧 app 名称 + 右侧工作区路径,整体垂直居中
        with Horizontal(id="title-bar"), Horizontal():
            yield Label(self.CONSOLE_TITLE, id="title-left")
            yield Label("工作区", id="title-right")

        # 输出区域
        yield RichLog(id="output", highlight=True, markup=True, wrap=True)

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
        log = self.query_one("#output", RichLog)
        tui_console = _TuiConsole(log)

        self.result_manager.console = tui_console

        # 更新标题栏右侧显示实际工作区路径
        title_right = self.query_one("#title-right", Label)
        title_right.update(f"工作区: {self.workspace.root_path}")

        # 创建 command handler
        self.command_handler = CommandHandler(
            self.workspace,
            self.tool_registry,
            self.result_manager,
            tui_console,  # type: ignore[arg-type]
            self,
        )
        self.command_handler.registry.register_many(
            [HelpCommand(self.command_handler.registry), ClsCommand(self.command_handler.registry)]
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

        if not text.strip():
            return

        text = self.paste_refence.expand(text).replace("&quot;", '"')
        self.paste_refence.clear()

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
        if self.paste_refence.should_collapse(text):
            text = self.paste_refence.collapsed(text)
        text_area.insert(text)

    def action_submit_text(self) -> None:
        """Ctrl+Enter 提交文本"""
        self._do_submit()

    def _maybe_finish_multiline(self) -> None:
        """检查多行缓冲区是否已完整"""
        if self._multiline_buffer[-1].strip().endswith("</func_call>"):
            full_input = "\n".join(self._multiline_buffer)
            self._multiline_buffer.clear()
            self._update_prompt(f"{self.CONSOLE_TITLE}>")
            self._dispatch(full_input)

    def _dispatch(self, user_input: str) -> None:
        """解析并执行一条完整的用户输入"""
        assert self.command_handler is not None
        assert self.tool_handler is not None

        parsed = parse_input(user_input, self.command_handler.registry)

        if parsed.is_command:
            self.command_handler.handle(parsed)
        else:
            self.tool_handler.handle(parsed)

    def _update_prompt(self, label: str) -> None:
        """更新提示符文本"""
        prompt_widget = self.query_one("#prompt-label", Label)
        prompt_widget.update(label)

    def action_quit_confirm(self) -> None:
        """退出应用"""
        log = self.query_one("#output", RichLog)
        log.write("[bold]再见![/bold]")
        self.exit()

    def _print_welcome(self) -> None:
        """在输出区域打印欢迎横幅"""
        log = self.query_one("#output", RichLog)
        assert self.command_handler is not None

        log.write(f"[bold green]{self.CONSOLE_TITLE}[/bold green]")
        log.write(f"[dim]工作区: {self.workspace.root_path}[/dim]")
        log.write("")
        log.write(_generate_help_text(self.command_handler.registry.list_commands()))
        log.write("[dim]输入 /help 查看命令,Ctrl+Q 退出[/dim]")
        log.write("")
