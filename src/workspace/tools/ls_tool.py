from pathlib import Path

from src.models.tool_error_response import ToolErrorResponse
from src.workspace.tools.base_tool import BaseTool
from src.workspace.workspace import Workspace


class LsTool(BaseTool):
    def __init__(self, workspace: Workspace):
        super().__init__(workspace, "ls", self.ls.__doc__)
        self.func = self.ls
        self.params = BaseTool.extract_params(self.ls)

    @BaseTool.handle_tool_exceptions
    def ls(self, folder_path: str = ".") -> list[str] | str:
        """
        列出指定目录下的文件和文件夹. 返回相对路径列表, 并标记[Folder]或[File]
        """
        path: Path = self.workspace.path_validator.validate(folder_path)
        if not path.is_dir():
            return ToolErrorResponse(self.__class__.__name__, f'参数错误: "{path}"不是一个目录').to_str()
        return [
            f"{'[Folder]' if item.is_dir() else '[File]'} {item.relative_to(self.workspace.root_path)}"
            for item in path.iterdir()
        ]
