"""ManualAid TUI Console Widget -- 功能完备的 Textual 控件"""

from __future__ import annotations

from typing import ClassVar

from rich.markdown import Markdown
from textual.containers import Vertical, Widget
from textual.widgets import Collapsible, RichLog, Static, TabbedContent, TabPane


class TuiConsole(Vertical):
    """功能完备的 TUI 控制台组件.

    包含:
    - Tab 1 (RichLog): 用于普通富文本日志.
    - Tab 2 (Tool Calls): 用于显示工具调用情况.
    """

    DEFAULT_CSS = """
    TuiConsole {
        height: 1fr;
        width: 1fr;
    }

    TuiConsole TabbedContent {
        height: 1fr;
    }

    TuiConsole TabbedContent > TabPane {
        padding: 0;
    }

    #tui-console-main-log {
        height: 1fr;
    }

    #tui-console-tool-calls {
        height: 1fr;
        overflow-y: auto;
    }
    """

    BINDINGS: ClassVar[list] = []

    def __init__(self) -> None:
        super().__init__()
        self._collapsible: dict[str, Collapsible] = {}

    def compose(self):
        with TabbedContent():
            with TabPane("RichLog", id="tab-richlog"):
                yield RichLog(id="tui-console-main-log", highlight=True, markup=True, wrap=True)
            with TabPane("Tool Calls", id="tab-tool-calls"):
                yield Vertical(id="tui-console-tool-calls")

    @property
    def main_log(self) -> RichLog:
        return self.query_one("#tui-console-main-log", RichLog)

    @property
    def tool_calls_container(self) -> Vertical:
        return self.query_one("#tui-console-tool-calls", Vertical)

    def print(self, *args) -> None:
        """将内容写入主日志区"""
        for arg in args:
            if isinstance(arg, str):
                self.main_log.write(arg)
            else:
                self.main_log.write(arg)

    def clear(self) -> None:
        """清空主日志区和工具调用区"""
        self.main_log.clear()
        self.tool_calls_container.remove_children()
        self._collapsible.clear()

    def print_collapsible(self, title: str, content: str, cid: str | None = None) -> None:
        """添加一个可折叠的输出块到工具调用标签页.

        Args:
            title: 折叠块的标题.
            content: 折叠块的内容,支持 Markdown.
            cid: 唯一 ID,用于后续定位.如果未提供,则自动生成.
        """
        if cid is None:
            cid = f"collapsible-{len(self._collapsible)}"

        # 确保 ID 唯一
        if cid in self._collapsible:
            cid = f"{cid}-{len(self._collapsible)}"

        # 使用 Markdown 渲染内容
        markdown_content = Markdown(content)
        content_widget = Static(markdown_content, id=f"tui-collapsible-content-{cid}")

        collapsible = Collapsible(content_widget, title=title, id=f"tui-collapsible-{cid}")

        self.tool_calls_container.mount(collapsible)
        self._collapsible[cid] = collapsible

        # 自动滚动到底部
        self.scroll_end(animate=False)

    def print_collapsible_with_widget(self, title: str, widget: Widget, cid: str | None = None) -> None:
        """添加一个可折叠的输出块到工具调用标签页.

        Args:
            title: 折叠块的标题.
            widget: 折叠块的内容控件
            cid: 唯一 ID,用于后续定位.如果未提供,则自动生成.
        """
        if cid is None:
            cid = f"collapsible-{len(self._collapsible)}"

        # 确保 ID 唯一
        if cid in self._collapsible:
            cid = f"{cid}-{len(self._collapsible)}"

        collapsible = Collapsible(widget, title=title, id=f"tui-collapsible-{cid}")

        self.tool_calls_container.mount(collapsible)
        self._collapsible[cid] = collapsible

        # 自动滚动到底部
        self.scroll_end(animate=False)
