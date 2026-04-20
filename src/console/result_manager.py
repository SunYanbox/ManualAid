import os
import time
from dataclasses import dataclass
from typing import Any


@dataclass
class ResultEntry:
    """Result history entry"""

    index: int
    func_name: str
    result: str
    timestamp: float
    copied: bool = False


# noinspection SpellCheckingInspection
def _copy_fallback(entry) -> bool:
    """Fallback clipboard copy using system commands"""
    import subprocess
    import sys

    try:
        if sys.platform == "win32":
            # Windows: 使用 clip 命令
            process = subprocess.Popen(["clip"], stdin=subprocess.PIPE, shell=True)
            process.communicate(input=entry.result.encode("utf-8"))
        elif sys.platform == "darwin":
            # macOS: 使用 pbcopy
            process = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
            process.communicate(input=entry.result.encode("utf-8"))
        else:
            # Linux: 使用 xclip 或 xsel
            process = subprocess.Popen(["xclip", "-selection", "clipboard"], stdin=subprocess.PIPE)
            process.communicate(input=entry.result.encode("utf-8"))

        entry.copied = True
        return True
    except Exception as e:
        print(f"复制过程中出现错误: {e.__class__.__name__}({e})")
        return False


def _to_string(result: Any) -> str:
    """Convert result to string"""
    if isinstance(result, str):
        return result
    try:
        return repr(result)
    except Exception:
        return str(result)


class ResultManager:
    """Result history manager (in-memory) with auto-cleanup"""

    def __init__(self):
        self._history: list[ResultEntry] = []
        self._next_index: int = 1
        self.EXPIRE_MINUTES = float(os.getenv("RESULT_EXPIRE_MINUTES", "5"))
        self.CLEANUP_MINUTES = float(os.getenv("RESULT_CLEANUP_MINUTES", "15"))
        self.AUTO_COPY = os.getenv("MANUALAID_AUTO_COPY", "TRUE").lower() in ("true", "1", "yes", "on")

    def add(self, func_name: str, result: Any) -> ResultEntry:
        """Add result to history"""
        result_str = _to_string(result)
        entry = ResultEntry(
            index=self._next_index,
            func_name=func_name,
            result=result_str,
            timestamp=time.time(),
        )
        self._history.append(entry)
        self._next_index += 1
        self._cleanup_expired()

        if self.AUTO_COPY and not func_name.startswith(("tool_prompt", "workspace_prompt")):
            self.copy_to_clipboard(entry.index)

        return entry

    def get(self, index: int) -> ResultEntry | None:
        """Get result by index"""
        for entry in self._history:
            if entry.index == index:
                return entry
        return None

    def copy_to_clipboard(self, index: int) -> bool:
        """Copy result to clipboard"""
        entry = self.get(index)
        if entry is None:
            return False

        try:
            import pyperclip

            pyperclip.copy(entry.result)
            entry.copied = True
            return True
        except ImportError:
            # 降级到系统命令
            return _copy_fallback(entry)

    def list_history(self) -> list[ResultEntry]:
        """List all history"""
        self._cleanup_expired()
        return self._history.copy()

    def _cleanup_expired(self) -> None:
        """Clean up expired entries"""
        now = time.time()
        expire_seconds = self.CLEANUP_MINUTES * 60
        self._history = [
            entry for entry in self._history if not (entry.copied and now - entry.timestamp > expire_seconds)
        ]
