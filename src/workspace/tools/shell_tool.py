"""Shell 命令执行工具 — 审核通过后执行."""

from src.models.tools.tool_result import ToolResult
from src.workspace.tools.base_tool import BaseTool
from src.workspace.workspace import Workspace


class ShellTool(BaseTool):
    """Shell 命令执行工具.

    所有 Shell 命令均需经过审核机制:
    1. 调用时创建 PENDING_AUDIT 记录, 不立即执行
    2. 审核 UI 中展示待审核命令
    3. 审核通过后实际执行命令并记录输出
    """

    def __init__(self, workspace: Workspace):
        super().__init__(workspace, "shell", self.shell.__doc__, write_permission=True)
        self.func = self.shell
        self.params = BaseTool.extract_params(self.shell)
        self.param_descriptions = {
            "command": "要执行的 Shell 命令",
            "description": "命令描述, 说明命令的目的和作用, 帮助审核人员理解命令意图",
        }

    @BaseTool.handle_tool_exceptions
    def shell(self, command: str, description: str = "") -> ToolResult:
        """
        执行 Shell 命令(需审核通过)
        """
        if not command or not command.strip():
            return self.make_failed_response(kwargs=locals().copy(), error=str(ValueError("command 不能为空")))

        session_id = self.workspace.session_id
        shell_id = self.workspace.db.record_shell_command(
            command=command.strip(),
            description=description.strip(),
            session_id=session_id,
        )

        preview_parts = [
            "命令已提交审核系统, 审核通过后将自动执行",
            "",
            f"[Shell Preview] ID: {shell_id}",
            f"Command: {command.strip()}",
        ]
        if description.strip():
            preview_parts.append(f"Description: {description.strip()}")

        return self.make_success_response(
            kwargs=locals().copy(),
            data="\n".join(preview_parts),
        )
