"""命令分发处理器"""

from typing import TYPE_CHECKING

from src.console.commands.base import CommandContext, CommandParseResult
from src.console.commands.registry import CommandRegistry

if TYPE_CHECKING:
    from src.console.result_manager import ResultManager
    from src.core.tool_registry import ToolRegistry
    from src.workspace.workspace import Workspace


class CommandHandler:
    """处理控制台命令的处理器"""

    def __init__(
        self,
        workspace: "Workspace",
        tool_registry: "ToolRegistry",
        result_manager: "ResultManager",
        console,  # 接受任何实现了 print/clear 的对象(_TuiConsole 或 rich.console.Console)
    ):
        self.workspace = workspace
        self.tool_registry = tool_registry
        self.result_manager = result_manager
        self.console = console
        self.registry = CommandRegistry.create_default()

    def handle(self, parsed_input: CommandParseResult) -> bool:
        """处理一条解析后的命令输入"""
        if not parsed_input.is_command:
            return False

        context = CommandContext(
            workspace=self.workspace,
            tool_registry=self.tool_registry,
            result_manager=self.result_manager,
            console=self.console,
            parsed_input=parsed_input,
        )

        result = self.registry.execute(parsed_input.command_type, context)

        if not result.success and result.message:
            self.console.print(f"[red]错误: {result.message}[/red]")

        return result.success
