"""Base classes for commands"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from rich.console import Console

    from src.console.result_manager import ResultManager
    from src.core.tool_registry import ToolRegistry
    from src.workspace.workspace import Workspace


@dataclass
class CommandParseResult:
    """命令解析结果"""

    source: str
    is_command: bool
    command_type: str | None = None
    func_name: str | None = None
    func_args: list[Any] | None = None
    func_kwargs: dict[str, Any] | None = None
    raw_input: str = ""


@dataclass
class CommandContext:
    """Command execution context"""

    workspace: "Workspace"
    tool_registry: "ToolRegistry"
    result_manager: "ResultManager"
    console: "Console"
    parsed_input: CommandParseResult


@dataclass
class CommandResult:
    """Result of command execution"""

    success: bool = True
    message: str | None = None
    should_exit: bool = False
    data: Any = None


class Command:
    """Base class for all commands"""

    name: str = ""
    aliases: list[str] = field(default_factory=list)
    description: str = ""
    usage: str = ""

    def can_handle(self, command_type: str) -> bool:
        """Check if this command can handle the given command type"""
        return command_type == self.name or command_type in self.aliases

    def execute(self, context: CommandContext) -> CommandResult:
        """Execute the command"""
        raise NotImplementedError("Subclasses must implement execute()")
