from src.core.launcher import launch
from src.models.commands import Command, CommandContext, CommandResult


class NewWindowCommand(Command):
    """Launch a new terminal window running ManualAid with specified workspace"""

    def __init__(self):
        super().__init__()
        self.name = "new"
        self.aliases = ["/new", "/n"]
        self.description = "Launch a new terminal window with ManualAid (optional workspace path)"
        self.usage = "/new [path]"

    def execute(self, context: CommandContext) -> CommandResult:
        # 解析工作区路径
        parts = context.parsed_input.source.split()
        workspace_path = parts[1] if len(parts) >= 2 else None
        if workspace_path is None:
            workspace_path = context.workspace.root_path

        try:
            if launch(workspace_path, context.console):
                return CommandResult(success=True, message="New window launched")
            else:
                return CommandResult(success=False, message="New window cant launched")
        except Exception as e:
            import traceback

            context.console.print(f"[bold red]{e}\n{traceback.format_exc()}[/bold red]")
            return CommandResult(success=False, message=str(e))
