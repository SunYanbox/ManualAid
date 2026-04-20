import re
from dataclasses import dataclass
from typing import Any

COPY_PATTERN = re.compile(r"^(?:/copy|/c)(?:\s+(\d+))?$")
VIEW_REMOVE_PATTERN = re.compile(r"^/view_remove\s+(\d+)$")


@dataclass
class CommandResult:
    """命令解析结果"""

    is_command: bool
    command_type: str | None = None
    func_name: str | None = None
    func_args: list[Any] | None = None
    func_kwargs: dict[str, Any] | None = None
    raw_input: str = ""


def parse_input(user_input: str) -> CommandResult:
    """Parse user input, distinguishing commands from tool calls"""
    user_input = user_input.strip()

    if not user_input:
        return CommandResult(is_command=False, raw_input=user_input)

    if user_input.startswith("<func_call>") and user_input.endswith("</func_call>"):
        return CommandResult(is_command=False, raw_input=user_input)

    # 匹配 /copy 或 /c,可选数字参数
    copy_match = COPY_PATTERN.match(user_input)
    if copy_match:
        index_str = copy_match.group(1)
        index = int(index_str) if index_str else None
        return CommandResult(
            is_command=True,
            command_type="copy",
            func_kwargs={"index": index},
            raw_input=user_input,
        )

    # 匹配 /view_remove
    view_remove_match = VIEW_REMOVE_PATTERN.match(user_input)
    if view_remove_match:
        index = int(view_remove_match.group(1))
        return CommandResult(
            is_command=True,
            command_type="view_remove",
            func_kwargs={"index": index},
            raw_input=user_input,
        )

    if user_input.startswith("/"):
        parts = user_input.split()
        cmd = parts[0].lower()

        if cmd in ("/help", "/h"):
            return CommandResult(is_command=True, command_type="help", raw_input=user_input)
        if cmd in ("/tools", "/t"):
            return CommandResult(is_command=True, command_type="tools", raw_input=user_input)
        if cmd in ("/tool",) and len(parts) > 1:
            return CommandResult(
                is_command=True,
                command_type="tool",
                func_kwargs={"name": parts[1]},
                raw_input=user_input,
            )
        if cmd in ("/prompt",):
            return CommandResult(is_command=True, command_type="prompt", raw_input=user_input)
        if cmd in ("/workspace", "/ws"):
            return CommandResult(is_command=True, command_type="workspace", raw_input=user_input)
        if cmd in ("/history",):
            return CommandResult(is_command=True, command_type="history", raw_input=user_input)
        if cmd in ("/quit", "/q", "/exit"):
            return CommandResult(is_command=True, command_type="quit", raw_input=user_input)
        if cmd in ("/view", "/v"):
            return CommandResult(is_command=True, command_type="view", raw_input=user_input)
        if cmd in ("/view_clear",):
            return CommandResult(is_command=True, command_type="view_clear", raw_input=user_input)

    return CommandResult(is_command=False, raw_input=user_input)
