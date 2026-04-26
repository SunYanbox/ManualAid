from itertools import islice

from src.models.tool_error_response import ToolErrorResponse
from src.workspace.path_validator import PathNotFoundError, WorkspaceBoundaryError
from src.workspace.tools.base_tool import BaseTool
from src.workspace.workspace import Workspace


class GlobTool(BaseTool):
    def __init__(self, workspace: Workspace):
        super().__init__(workspace, "glob", self.glob.__doc__)
        self.func = self.glob
        self.params = BaseTool.extract_params(self.glob)

    def glob(self, pattern: str, folder_path: str = ".", max_ret: int = 1000) -> list[str]:
        """
        在工作区内按通配符模式匹配并列出所有路径,带[Folder]或[File]的类型标记. 失败时返回错误信息

        Parameters
        ----------
        pattern: 通配符
        folder_path: 目录路径
        max_ret: 最多返回多少条检索结果

        Returns
        -------
        检索到的文件或文件夹的相对路径
        """
        try:
            root_path = self.workspace.path_validator.validate(folder_path)
            if not root_path.is_dir():
                return ToolErrorResponse(self.__class__.__name__, f"{root_path}不是一个文件夹路径").to_str()

            return [
                f"{'[Folder]' if item.is_dir() else '[File]'} {item.relative_to(self.workspace.root_path)}"
                for item in islice(root_path.glob(pattern), max_ret)
            ]
        except PathNotFoundError as err1:
            return ToolErrorResponse(self.__class__.__name__, err1).to_str()
        except WorkspaceBoundaryError as err2:
            return ToolErrorResponse(self.__class__.__name__, err2).to_str()
        except PermissionError as err3:
            return ToolErrorResponse(self.__class__.__name__, err3).to_str()
        except Exception as err:
            return ToolErrorResponse(self.__class__.__name__, err).to_str()
