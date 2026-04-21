from pathlib import Path

from src.constants.tools_docs import Write_TOOL
from src.core.tool_error_response import ToolErrorResponse
from src.workspace.path_validator import PathNotFoundError, WorkspaceBoundaryError
from src.workspace.tools.base_tool import BaseTool
from src.workspace.workspace import Workspace


class WriteTool(BaseTool):
    def __init__(self, workspace: Workspace):
        super().__init__(workspace, *Write_TOOL)
        self.func = self.write
        self.params = BaseTool.extract_params(self.write)

    def write(self, path: str, context: str = "") -> str:
        try:
            file_path: Path = self.workspace.path_validator.validate(path, create_file_if_not_exist=True)
            if not file_path.is_file():
                return ToolErrorResponse(
                    self.__class__.__name__, f'"{path}"不是文件路径, 请检查是否输错了文件夹路径'
                ).to_str()
            with open(file_path, mode="w", encoding="utf-8") as file:
                file.write(context)
            return "write success"
        except PathNotFoundError as err1:
            return ToolErrorResponse(self.__class__.__name__, err1).to_str()
        except WorkspaceBoundaryError as err2:
            return ToolErrorResponse(self.__class__.__name__, err2).to_str()
        except PermissionError as err3:
            return ToolErrorResponse(self.__class__.__name__, err3).to_str()
        except Exception as err:
            return ToolErrorResponse(self.__class__.__name__, err).to_str()
