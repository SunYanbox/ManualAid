from itertools import islice

from src.models.tools.tool_result import ToolResult
from src.workspace.tools.base_tool import BaseTool
from src.workspace.workspace import Workspace


class GlobTool(BaseTool):
    def __init__(self, workspace: Workspace):
        super().__init__(workspace, "glob", self.glob.__doc__)
        self.func = self.glob
        self.params = BaseTool.extract_params(self.glob)
        self.param_descriptions = {
            "pattern": "通配符",
            "path": "目录路径",
            "max_ret": "最多返回多少条检索结果",
        }
        self._exclusion_manager = workspace.exclusion_manager

    @BaseTool.handle_tool_exceptions
    def glob(self, pattern: str, path: str = ".", max_ret: int = 1000) -> ToolResult:
        """
        在工作区内按通配符模式匹配并列出所有路径,带[Folder]或[File]的类型标记. 失败时返回错误信息
        """
        root_path = self.workspace.path_validator.validate(path)
        if not root_path.is_dir():
            return self.make_failed_response(kwargs=locals().copy(), error=f"{root_path}不是一个文件夹路径")

        return self.make_success_response(
            kwargs=locals().copy(),
            data=[
                f"{'[Folder]' if item.is_dir() else '[File]'} {item.relative_to(self.workspace.root_path)}"
                for item in islice(root_path.glob(pattern), max_ret)
                if not self._exclusion_manager.should_exclude_path(item)
            ],
        )
