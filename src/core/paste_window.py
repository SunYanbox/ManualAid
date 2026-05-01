import threading
import tkinter as tk
from collections.abc import Callable
from tkinter import scrolledtext


class PasteWindow:
    """超大文本粘贴窗口,单例模式,每次关闭后完全销毁线程和Tk实例"""

    _instance: PasteWindow | None = None
    _current_thread: threading.Thread | None = None
    _current_root: tk.Tk | None = None

    def __init__(self):
        self._callback: Callable[[str], None] | None = None
        self._window: tk.Toplevel | None = None
        self._text_widget: scrolledtext.ScrolledText | None = None
        self._stats_label: tk.Label | None = None

    @classmethod
    def get_instance(cls) -> PasteWindow:
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _run_tkinter(self, initial_text: str, title: str) -> None:
        """在独立线程中运行 tkinter 事件循环"""
        # 创建新的 Tk 实例
        root = tk.Tk()
        root.withdraw()  # 隐藏主窗口
        PasteWindow._current_root = root

        # 创建粘贴窗口
        window = tk.Toplevel(root)
        window.title(title)
        window.geometry("800x600")
        window.minsize(400, 300)
        self._window = window

        # 创建文本区域
        frame = tk.Frame(window)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        text_widget = scrolledtext.ScrolledText(
            frame, wrap=tk.WORD, font=("Consolas", 11), undo=True, autoseparators=True, maxundo=100
        )
        text_widget.pack(fill="both", expand=True)
        self._text_widget = text_widget

        if initial_text:
            text_widget.insert(1.0, initial_text)

        # 按钮框架
        button_frame = tk.Frame(window)
        button_frame.pack(fill="x", padx=10, pady=(0, 10))

        # 统计信息标签
        stats_label = tk.Label(button_frame, text="字符数: 0", fg="gray")
        stats_label.pack(side="left", padx=5)
        self._stats_label = stats_label

        # 按钮
        copy_btn = tk.Button(button_frame, text="复制文本", command=self._copy_to_clipboard)
        copy_btn.pack(side="right", padx=5)

        clear_btn = tk.Button(button_frame, text="清空", command=self._clear_text)
        clear_btn.pack(side="right", padx=5)

        cancel_btn = tk.Button(button_frame, text="取消", command=self._on_cancel)
        cancel_btn.pack(side="right", padx=5)

        confirm_btn = tk.Button(button_frame, text="确认粘贴", command=self._on_confirm, bg="#4CAF50", fg="white")
        confirm_btn.pack(side="right", padx=5)

        # 绑定快捷键
        window.bind("<Control-a>", lambda e: self._select_all())
        window.bind("<Escape>", lambda e: self._on_cancel())
        window.bind("<Control-Return>", lambda e: self._on_confirm())

        # 窗口关闭事件
        window.protocol("WM_DELETE_WINDOW", self._on_cancel)

        # 更新统计信息的绑定
        text_widget.bind("<KeyRelease>", lambda e: self._update_stats())

        # 初始更新统计
        self._update_stats()

        # 设置焦点
        text_widget.focus_set()

        # 启动 tkinter 事件循环
        try:
            root.mainloop()
        except tk.TclError:
            pass
        finally:
            # 清理资源
            try:
                if root.winfo_exists():
                    root.destroy()
            except Exception:
                pass
            PasteWindow._current_root = None
            self._window = None
            self._text_widget = None
            self._stats_label = None
            PasteWindow._current_thread = None

    def _copy_to_clipboard(self) -> None:
        """复制到剪贴板"""
        content = self.get_text()
        if content and self._window:
            try:
                self._window.clipboard_clear()
                self._window.clipboard_append(content)
                self._show_temporary_message("已复制")
            except Exception:
                pass

    def _show_temporary_message(self, message: str) -> None:
        """显示临时消息"""
        if self._stats_label and self._stats_label.winfo_exists():
            original = self._stats_label.cget("text")
            self._stats_label.config(text=f"✓ {message}", fg="green")
            if self._window:
                self._window.after(1500, lambda: self._stats_label.config(text=original, fg="gray"))

    def _on_confirm(self) -> None:
        """确认"""
        content = self.get_text()
        if self._callback:
            self._callback(content)
        self.hide()

    def _on_cancel(self) -> None:
        """取消"""
        self.hide()

    def _update_stats(self) -> None:
        """更新统计"""
        if self._text_widget and self._text_widget.winfo_exists():
            try:
                content = self._text_widget.get(1.0, tk.END)
                char_count = len(content) - 1
                line_count = int(self._text_widget.index(tk.END).split(".")[0]) - 1
                kb_size = char_count / 1024
                size_text = f"{kb_size:.1f}KB" if kb_size >= 1 else f"{char_count}B"
                self._stats_label.config(text=f"字符数: {char_count:,} ({size_text}) | 行数: {line_count}")
            except Exception:
                pass

    def _clear_text(self) -> None:
        """清空"""
        if self._text_widget and self._text_widget.winfo_exists():
            self._text_widget.delete(1.0, tk.END)
            self._update_stats()

    def _select_all(self) -> str | None:
        """全选"""
        if self._text_widget and self._text_widget.winfo_exists():
            self._text_widget.tag_add(tk.SEL, "1.0", tk.END)
            self._text_widget.mark_set(tk.INSERT, "1.0")
            return "break"
        return None

    def get_text(self) -> str:
        """获取文本"""
        if self._text_widget and self._text_widget.winfo_exists():
            content = self._text_widget.get(1.0, tk.END)
            if content.endswith("\n"):
                content = content[:-1]
            return content
        return ""

    def show(
        self, callback: Callable[[str], None] | None = None, initial_text: str = "", title: str = "粘贴超大文本"
    ) -> None:
        """
        显示粘贴窗口(独立线程,非阻塞)

        每次调用都会创建新的线程和Tk实例,确保不会出现线程冲突
        """
        self._callback = callback

        # 如果已有窗口在运行,先关闭
        if PasteWindow._current_thread and PasteWindow._current_thread.is_alive():
            self.hide()
            # 等待线程完全结束
            PasteWindow._current_thread.join(timeout=1.0)

        # 创建新线程
        PasteWindow._current_thread = threading.Thread(
            target=self._run_tkinter, args=(initial_text, title), daemon=True
        )
        PasteWindow._current_thread.start()

    def hide(self) -> None:
        """关闭窗口"""
        if self._window and self._window.winfo_exists():
            try:
                self._window.quit()  # 退出 mainloop
                self._window.destroy()
            except Exception:
                pass

        # 等待线程结束,避免资源冲突
        if PasteWindow._current_thread and PasteWindow._current_thread != threading.current_thread():
            PasteWindow._current_thread.join(timeout=0.5)


# 便捷函数
_paste_window: PasteWindow | None = None


def show_paste_window(callback: Callable[[str], None] | None = None, initial_text: str = "") -> None:
    """显示粘贴窗口(非阻塞)"""
    global _paste_window
    if _paste_window is None:
        _paste_window = PasteWindow.get_instance()
    _paste_window.show(callback=callback, initial_text=initial_text)


def close_paste_window() -> None:
    """关闭粘贴窗口"""
    global _paste_window
    if _paste_window:
        _paste_window.hide()
