"""Result-related commands (copy, history, view)"""

import warnings
from argparse import ArgumentParser

from src.core.copy2clip import copy_to_clipboard
from src.models.commands import Command, CommandContext, CommandResult


class CopyCommand(Command):
    """Copy result to clipboard"""

    def __init__(self):
        super().__init__()
        self.name = "copy"
        self.aliases = ["/copy", "/c"]
        self.description = "复制历史工具记录或者工具标准调用格式到剪切板"
        self.usage = "/copy <n> or /c <n>"
        self.argparse = ArgumentParser("copy")
        self.argparse.add_argument("-i", "--index", dest="index", type=int, default=None, help="复制历史记录到剪切板")
        self.argparse.add_argument("-t", "--tool", dest="tool", default=None, help="复制指定工具的标准调用格式到剪切板")

    def execute(self, context: CommandContext) -> CommandResult:
        format_help: str = self.argparse.format_help()

        if "-h" in context.parsed_input.source or "--help" in context.parsed_input.source:
            context.console.print(format_help)
            return CommandResult(success=True)

        cmd, kwargs = self.parse(context.parsed_input.source)

        if cmd not in ["/copy", "/c"]:
            raise ValueError(f"不适配{self.__class__.__name__}的命令: {context.parsed_input.source}")

        index = kwargs.get("index", None)
        tool = kwargs.get("tool", None)

        if tool is not None and len(tool) > 0:
            for tool_names in context.tool_registry.list_tools().values():
                for tool_name in tool_names:
                    if tool == tool_name:
                        tool_obj = context.tool_registry.get_tool_info(tool_name)
                        if tool_obj:
                            copy_to_clipboard(tool_obj.to_func_call())
                            return CommandResult(success=False, message=f"已成功复制工具{tool_name}的标准调用格式")
            warn = (
                f"使用{self.__class__.__name__}时, 传入的参数tool({tool})"
                f"不存在于工具{context.tool_registry.list_tools()}中"
                f"或对应的已注册工具意外被删除"
            )
            context.console.print(f"[yellow]{warn}[/yellow]")
            warnings.warn(warn, stacklevel=2)

        if index is None:
            history = context.result_manager.list_history()
            if not history:
                context.console.print("[yellow]没有可复制的历史记录[/yellow]")
                return CommandResult(success=False, message=f"无历史记录\n{format_help}")
            index = history[-1].index

        if context.result_manager.copy_to_clipboard(index):
            context.console.print(f"[green]已复制历史记录 #{index}[/green]")
            return CommandResult(success=True)
        else:
            context.console.print(f"[red]复制历史记录 #{index} 失败\n{format_help}[/red]")
            return CommandResult(success=False, message="复制失败")


class HistoryCommand(Command):
    """Show command history"""

    def __init__(self):
        super().__init__()
        self.name = "history"
        self.aliases = ["/history"]
        self.description = "Show command history"
        self.usage = "/history"

    def execute(self, context: CommandContext) -> CommandResult:
        history = context.result_manager.list_history()
        if not history:
            context.console.print("[dim]No history yet.[/dim]")
            return CommandResult(success=True)

        for entry in history:
            copied_mark = " [copied]" if entry.copied else ""
            context.console.print(f"[bold cyan]{entry.index}:[/bold cyan] [bold]{entry.func_name}[/bold]{copied_mark}")
        return CommandResult(success=True)


@warnings.deprecated("将被抛弃的命令, 改为UI")
class ViewCommand(Command):
    """Open interactive result viewer"""

    def __init__(self):
        super().__init__()
        self.name = "view"
        self.aliases = ["/view", "/v"]
        self.description = "Open interactive result viewer"
        self.usage = "/view or /v"

    def execute(self, context: CommandContext) -> CommandResult:
        return CommandResult(success=True, message="已弃用命令返回值")


@warnings.deprecated("将被抛弃的命令, 改为UI")
class ViewClearCommand(Command):
    """Clear all items from viewer"""

    def __init__(self):
        super().__init__()
        self.name = "view_clear"
        self.aliases = ["/view_clear"]
        self.description = "Clear all items from viewer"
        self.usage = "/view_clear"

    def execute(self, context: CommandContext) -> CommandResult:
        return CommandResult(success=True, message="已弃用命令返回值")


@warnings.deprecated("将被抛弃的命令, 改为UI")
class ViewRemoveCommand(Command):
    """Remove specific item from viewer"""

    def __init__(self):
        super().__init__()
        self.name = "view_remove"
        self.aliases = ["/view_remove"]
        self.description = "Remove item from viewer"
        self.usage = "/view_remove <n>"

    def execute(self, context: CommandContext) -> CommandResult:
        return CommandResult(success=True, message="已弃用命令返回值")
