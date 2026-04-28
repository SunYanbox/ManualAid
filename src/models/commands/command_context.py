from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from textual.app import App

if TYPE_CHECKING:
    from src.console.commands.command_registry import CommandRegistry
    from src.console.result_manager import ResultManager
    from src.core.tool_registry import ToolRegistry
    from src.models.commands.command_parse_result import CommandParseResult
    from src.workspace.workspace import Workspace


@dataclass
class CommandContext:
    """Command execution context"""

    workspace: Workspace
    tool_registry: ToolRegistry
    result_manager: ResultManager
    console: Any
    command_registry: CommandRegistry
    parsed_input: CommandParseResult
    app: App | None
