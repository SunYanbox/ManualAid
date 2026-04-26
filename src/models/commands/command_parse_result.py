from dataclasses import dataclass
from typing import Any


@dataclass
class CommandParseResult:
    """命令解析结果"""

    source: str
    is_command: bool
    is_func: bool
    command_type: str | None = None
    func_name: str | None = None
    cmd_kwargs: dict[str, Any] | None = None
    funcs: list[tuple[str, dict[str, Any]]] | None = None
