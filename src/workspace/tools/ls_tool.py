from pathlib import Path

from src.models.tools.tool_result import ToolResult
from src.workspace.tools.base_tool import BaseTool
from src.workspace.workspace import Workspace


class LsTool(BaseTool):
    def __init__(self, workspace: Workspace):
        super().__init__(workspace, "ls", self.ls.__doc__)
        self.func = self.ls
        self.params = BaseTool.extract_params(self.ls)
        self.param_descriptions = {
            "path": "目录路径",
        }
        self._exclusion_manager = workspace.exclusion_manager

    @BaseTool.handle_tool_exceptions
    def ls(self, path: str = ".") -> ToolResult:
        """
        列出指定目录下的文件和文件夹. 返回相对路径列表, 并标记[Folder]或[File]
        """
        folder_path: Path = self.workspace.path_validator.validate(path)
        if not folder_path.is_dir():
            return self.make_failed_response(kwargs=locals().copy(), error=f'参数错误: "{folder_path}"不是一个目录')
        return self.make_success_response(
            kwargs=locals().copy(),
            data=[f"{'[Folder]' if item.is_dir() else '[File]'} {item.relative_to(self.workspace.root_path)}" for item in folder_path.iterdir() if not self._exclusion_manager.should_exclude_path(item)],
        )
