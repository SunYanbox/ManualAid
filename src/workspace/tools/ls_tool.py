from pathlib import Path

from src.constants.tools_docs import LS_TOOL
from src.core.tool_error_response import ToolErrorResponse
from src.workspace.path_validator import PathNotFoundError, WorkspaceBoundaryError
from src.workspace.tools.base_tool import BaseTool
from src.workspace.workspace import Workspace


class LsTool(BaseTool):
    def __init__(self, workspace: Workspace):
        super().__init__(workspace, *LS_TOOL)
        self.func = self.ls
        self.params = BaseTool.extract_params(self.ls)

    def ls(self, folder_path: str = ".") -> list[str] | str:
        try:
            path: Path = self.workspace.path_validator.validate(folder_path)
            if not path.is_dir():
                raise ValueError(f"{path} is not a directory")
            return [
                f"{'[Folder]' if item.is_dir() else '[File]'} {item.relative_to(self.workspace.root_path)}"
                for item in path.iterdir()
            ]
        except PathNotFoundError as err1:
            return ToolErrorResponse(self.__class__.__name__, err1).to_str()
        except WorkspaceBoundaryError as err2:
            return ToolErrorResponse(self.__class__.__name__, err2).to_str()
        except PermissionError as err3:
            return ToolErrorResponse(self.__class__.__name__, err3).to_str()
        except Exception as err:
            return ToolErrorResponse(self.__class__.__name__, err).to_str()
