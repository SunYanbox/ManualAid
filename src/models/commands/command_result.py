from dataclasses import dataclass
from typing import Any


@dataclass
class CommandResult:
    """Result of command execution"""

    success: bool = True
    message: str | None = None
    should_exit: bool = False
    data: Any = None
