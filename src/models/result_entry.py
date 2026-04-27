from dataclasses import dataclass


@dataclass
class ResultEntry:
    """Result history entry"""

    index: int
    func_name: str
    result: str
    timestamp: float
    copied: bool = False
