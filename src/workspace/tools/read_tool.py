from pathlib import Path

from src.constants.tools_docs import READ_TOOL
from src.core.tool_error_response import ToolErrorResponse
from src.workspace.path_validator import PathNotFoundError, WorkspaceBoundaryError
from src.workspace.tools.base_tool import BaseTool
from src.workspace.workspace import Workspace


class ReadTool(BaseTool):
    def __init__(self, workspace: Workspace):
        super().__init__(workspace, *READ_TOOL)
        self.func = self.read
        self.params = BaseTool.extract_params(self.read)

    def read(self, file_path: str, max_size=0, encoding="utf-8") -> str:
        try:
            path: Path = self.workspace.path_validator.validate(file_path)
            content = ToolErrorResponse(self.__class__.__name__, f"读取文件{file_path}时未读取到完整文件").to_str()
            if max_size > 0:
                # 按行读取,只读取前 max_size 行
                lines = []
                with open(path, encoding=encoding) as f:
                    for i, line in enumerate(f):
                        if i >= max_size:
                            break
                        lines.append(line)
                content = "".join(lines)
            else:
                # 读取整个文件
                with open(path, encoding=encoding) as f:
                    content: str = f.read()
            return content
        except PathNotFoundError as err1:
            return ToolErrorResponse(self.__class__.__name__, err1).to_str()
        except WorkspaceBoundaryError as err2:
            return ToolErrorResponse(self.__class__.__name__, err2).to_str()
        except PermissionError as err3:
            return ToolErrorResponse(self.__class__.__name__, err3).to_str()
        except Exception as err:
            return ToolErrorResponse(self.__class__.__name__, err).to_str()
