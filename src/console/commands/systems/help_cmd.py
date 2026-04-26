from src.models.commands import Command, CommandContext, CommandResult
from src.utils.generate_help_text import generate_help_text


class HelpCommand(Command):
    """显示帮助信息"""

    def __init__(self):
        super().__init__()
        self.name = "help"
        self.aliases = ["/help", "/h", "/?"]
        self.description = "显示帮助信息"
        self.usage = "/help 或 /h 或 /?"

    def execute(self, context: CommandContext) -> CommandResult:
        context.console.print(generate_help_text(context.command_registry.list_commands()))
        return CommandResult(success=True)
