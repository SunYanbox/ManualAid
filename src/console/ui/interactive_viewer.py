"""交互式结果查看器 - 通用可折叠控件"""

from dataclasses import dataclass

import keyboard
from rich.align import Align
from rich.console import Console, Group
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text
from typing_extensions import deprecated

console = Console()


@dataclass
@deprecated("将要弃用")
class ViewerItem:
    """查看器项目"""

    id: str  # 唯一标识符
    title: str  # 标题(已格式化的 Rich markup)
    content: str  # 内容(纯文本或代码)
    language: str | None = None  # 语法高亮语言,None 表示纯文本
    expanded: bool = False  # 是否展开
    selected: bool = False  # 是否选中

    def render(self) -> Panel:
        """渲染为 Panel"""
        expand_icon = "▼" if self.expanded else "▶"
        full_title = f"{expand_icon} {self.title}"

        if self.expanded:
            # 展开状态:显示完整内容
            if self.language:
                content = Syntax(self.content, self.language, theme="monokai", line_numbers=True, word_wrap=True)
            else:
                content = self.content

            border_style = "cyan" if self.selected else "green"
        else:
            # 折叠状态:显示预览
            lines = self.content.split("\n")
            preview_lines = lines[:3]
            preview = "\n".join(preview_lines)

            if len(lines) > 3:
                preview += f"\n[dim]... ({len(lines) - 3} more lines, press Enter to expand)[/dim]"

            content = preview
            border_style = "yellow" if self.selected else "dim"

        return Panel(content, title=full_title, border_style=border_style)

    def toggle(self):
        """切换展开/折叠状态"""
        self.expanded = not self.expanded


@deprecated("将要弃用")
class InteractiveViewer:
    """通用交互式查看器"""

    def __init__(self, title: str = "Interactive Viewer"):
        self.title = title
        self.items: list[ViewerItem] = []
        self.selected_index = 0
        self.running = False

    def add_item(self, id: str, title: str, content: str, language: str | None = None) -> None:
        """添加项目

        Args:
            id: 唯一标识符
            title: 标题(支持 Rich markup)
            content: 内容文本
            language: 语法高亮语言(如 'python', 'json', 'markdown' 等)
        """
        item = ViewerItem(id=id, title=title, content=content, language=language, expanded=False, selected=False)
        self.items.append(item)

    def remove_item(self, id: str) -> bool:
        """移除项目"""
        for i, item in enumerate(self.items):
            if item.id == id:
                self.items.pop(i)
                if self.selected_index >= len(self.items):
                    self.selected_index = max(0, len(self.items) - 1)
                return True
        return False

    def clear(self) -> None:
        """清空所有项目"""
        self.items.clear()
        self.selected_index = 0

    def get_item(self, id: str) -> ViewerItem | None:
        """获取项目"""
        for item in self.items:
            if item.id == id:
                return item
        return None

    def _render_layout(self) -> Layout:
        """渲染布局"""
        layout = Layout()

        # 创建项目列表面板
        if self.items:
            # 更新选中状态
            for i, item in enumerate(self.items):
                item.selected = i == self.selected_index

            panels_group = Group(*[item.render() for item in self.items])

            stats = f"Total: {len(self.items)} | Selected: #{self.selected_index + 1}"
            if self.items[self.selected_index].expanded:
                stats += " [Expanded]"
            else:
                stats += " [Collapsed]"
        else:
            panels_group = Panel(Align.center("[dim]No items to display[/dim]"), border_style="dim")
            stats = "No items"

        # 分割布局
        layout.split(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=3),
        )

        # 头部
        header_text = Text()
        header_text.append(f"[bold]{self.title}[/bold]\n")
        header_text.append(
            "[dim]↑/↓: Navigate • Enter: Expand/Collapse • Space: Toggle • Delete: Remove • q/Esc: Quit[/dim]"
        )

        layout["header"].update(Panel(Align.center(header_text), border_style="blue"))

        # 主体
        layout["body"].update(Panel(panels_group, title=f"Items ({len(self.items)})", border_style="cyan"))

        # 底部
        footer_text = Text()
        footer_text.append(stats, style="dim")

        if self.items:
            current_item = self.items[self.selected_index]
            footer_text.append(f"\n[dim]Current: {current_item.id}[/dim]")

        layout["footer"].update(Panel(footer_text, border_style="dim"))

        return layout

    def run(self) -> None:
        """运行交互式查看器"""
        if not self.items:
            console.print("[yellow]No items to display[/yellow]")
            return

        self.running = True

        # 隐藏光标
        console.show_cursor(False)

        try:
            with Live(self._render_layout(), refresh_per_second=30, screen=True) as live:
                while self.running:
                    try:
                        # 处理键盘事件
                        if keyboard.is_pressed("up"):
                            self._move_selection(-1)
                            live.update(self._render_layout())
                            self._wait_key_release("up")
                        elif keyboard.is_pressed("down"):
                            self._move_selection(1)
                            live.update(self._render_layout())
                            self._wait_key_release("down")
                        elif keyboard.is_pressed("enter"):
                            if self.items:
                                self.items[self.selected_index].toggle()
                                live.update(self._render_layout())
                            self._wait_key_release("enter")
                        elif keyboard.is_pressed("space"):
                            if self.items:
                                self.items[self.selected_index].toggle()
                                live.update(self._render_layout())
                            self._wait_key_release("space")
                        elif keyboard.is_pressed("delete"):
                            if self.items:
                                removed_id = self.items[self.selected_index].id
                                self.remove_item(removed_id)
                                if not self.items:
                                    self.running = False
                                live.update(self._render_layout())
                            self._wait_key_release("delete")
                        elif keyboard.is_pressed("q") or keyboard.is_pressed("esc"):
                            self.running = False
                            self._wait_key_release("q")
                            self._wait_key_release("esc")
                        elif keyboard.is_pressed("home"):
                            if self.items:
                                self.selected_index = 0
                                live.update(self._render_layout())
                            self._wait_key_release("home")
                        elif keyboard.is_pressed("end"):
                            if self.items:
                                self.selected_index = len(self.items) - 1
                                live.update(self._render_layout())
                            self._wait_key_release("end")
                    except KeyboardInterrupt:
                        self.running = False
                        break
                    except Exception as e:
                        console.print(f"[red]Error: {e}[/red]")
        finally:
            # 恢复光标
            console.show_cursor(True)

    def _move_selection(self, delta: int) -> None:
        """移动选择"""
        if not self.items:
            return

        self.selected_index = (self.selected_index + delta) % len(self.items)

    def _wait_key_release(self, key: str) -> None:
        """等待按键释放"""
        import time

        timeout = time.time() + 0.5
        while keyboard.is_pressed(key):
            if time.time() > timeout:
                break
            time.sleep(0.01)


# 全局查看器实例
_global_viewer: InteractiveViewer | None = None


@deprecated("将要弃用")
def get_viewer(title: str = "ManualAid Result Viewer") -> InteractiveViewer:
    """获取全局查看器实例(单例)"""
    global _global_viewer
    if _global_viewer is None:
        _global_viewer = InteractiveViewer(title)
    return _global_viewer


@deprecated("将要弃用")
def add_to_viewer(id: str, title: str, content: str, language: str | None = None) -> None:
    """添加到全局查看器

    Args:
        id: 唯一标识符
        title: 标题(Rich markup 格式)
        content: 内容
        language: 语法高亮语言
    """
    viewer = get_viewer()
    viewer.add_item(id, title, content, language)


@deprecated("将要弃用")
def run_viewer() -> None:
    """运行全局查看器"""
    viewer = get_viewer()
    viewer.run()


@deprecated("将要弃用")
def clear_viewer() -> None:
    """清空查看器"""
    viewer = get_viewer()
    viewer.clear()
