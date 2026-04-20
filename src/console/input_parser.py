import re

from src.console.commands.base import CommandParseResult
from src.console.commands.registry import CommandRegistry

COPY_PATTERN = re.compile(r"^(?:/copy|/c)(?:\s+(\d+))?$")
VIEW_REMOVE_PATTERN = re.compile(r"^/view_remove\s+(\d+)$")


def parse_input(user_input: str, cmd_register: CommandRegistry) -> CommandParseResult:
    """Parse user input, distinguishing commands from tool calls"""
    user_input = user_input.strip()

    if not user_input:
        return CommandParseResult(source=user_input, is_command=False, raw_input=user_input)

    if user_input.startswith("<func_call>") and user_input.endswith("</func_call>"):
        return CommandParseResult(source=user_input, is_command=False, raw_input=user_input)

    # 匹配 /copy 或 /c,可选数字参数
    copy_match = COPY_PATTERN.match(user_input)
    if copy_match:
        index_str = copy_match.group(1)
        index = int(index_str) if index_str else None
        return CommandParseResult(
            source=user_input,
            is_command=True,
            command_type="copy",
            func_kwargs={"index": index},
            raw_input=user_input,
        )

    # 匹配 /view_remove
    view_remove_match = VIEW_REMOVE_PATTERN.match(user_input)
    if view_remove_match:
        index = int(view_remove_match.group(1))
        return CommandParseResult(
            source=user_input,
            is_command=True,
            command_type="view_remove",
            func_kwargs={"index": index},
            raw_input=user_input,
        )

    if user_input.startswith("/"):
        parts = user_input.split()
        cmd = parts[0].lower()

        for maybe_cmd in cmd_register.list_commands():
            if cmd in maybe_cmd.aliases:
                return CommandParseResult(
                    source=user_input, is_command=True, command_type=maybe_cmd.name, raw_input=user_input
                )

    return CommandParseResult(source=user_input, is_command=False, raw_input=user_input)
