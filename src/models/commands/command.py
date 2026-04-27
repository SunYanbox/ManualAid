import shlex
from argparse import ArgumentParser
from dataclasses import field
from typing import Any

from src.models.commands.command_context import CommandContext
from src.models.commands.command_result import CommandResult


class Command:
    """Base class for all commands"""

    name: str = ""
    aliases: list[str] = field(default_factory=list)
    description: str = ""
    usage: str = ""
    argparse: ArgumentParser | None = None

    def parse(self, command: str) -> tuple[str | None, dict[str, Any]]:
        parts = shlex.split(command)
        if not parts:
            return None, {}

        cmd_name = parts[0]
        args = parts[1:]

        try:
            parsed, _ = self.argparse.parse_known_args(args)
            kwargs = {k: v for k, v in vars(parsed).items() if v is not None and v is not False}
            return cmd_name, kwargs
        except Exception as e:
            raise ValueError(f"解析命令{self.__class__.__name__}({command})参数失败: {e}") from e

    def can_handle(self, command_type: str) -> bool:
        """Check if this command can handle the given command type"""
        return command_type == self.name or command_type in self.aliases

    def execute(self, context: CommandContext) -> CommandResult:
        """Execute the command"""
        raise NotImplementedError("Subclasses must implement execute()")
