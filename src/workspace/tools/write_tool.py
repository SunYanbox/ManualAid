from pathlib import Path

from src.core.tool_error_response import ToolErrorResponse
from src.workspace.path_validator import PathNotFoundError, WorkspaceBoundaryError
from src.workspace.tools.base_tool import BaseTool
from src.workspace.workspace import Workspace


class WriteTool(BaseTool):
    def __init__(self, workspace: Workspace):
        super().__init__(workspace, "write", self.write.__doc__, False, True)
        self.func = self.write
        self.params = BaseTool.extract_params(self.write)

    def write(self, file_path: str, content: str = "") -> str:
        """
        向文件写入内容, 注意:此操作会[覆盖]原文件内容,用户没有要求的情况下禁止使用

        Parameters
        ----------
        file_path: 要写入的文件路径
        content: 写入的文本内容
        """
        try:
            file_path: Path = self.workspace.path_validator.validate(file_path, create_file_if_not_exist=True)
            if not file_path.is_file():
                return ToolErrorResponse(
                    self.__class__.__name__, f'"{file_path}"不是文件路径, 请检查是否输错了文件夹路径'
                ).to_str()
            with open(file_path, mode="w", encoding="utf-8") as file:
                file.write(content)
            return "write success"
        except PathNotFoundError as err1:
            return ToolErrorResponse(self.__class__.__name__, err1).to_str()
        except WorkspaceBoundaryError as err2:
            return ToolErrorResponse(self.__class__.__name__, err2).to_str()
        except PermissionError as err3:
            return ToolErrorResponse(self.__class__.__name__, err3).to_str()
        except Exception as err:
            return ToolErrorResponse(self.__class__.__name__, err).to_str()
