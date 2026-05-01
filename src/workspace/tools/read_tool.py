from pathlib import Path

from src.models.tool_error_response import ToolErrorResponse
from src.workspace.path_validator import PathNotFoundError, WorkspaceBoundaryError
from src.workspace.tools.base_tool import BaseTool
from src.workspace.workspace import Workspace


class ReadTool(BaseTool):
    def __init__(self, workspace: Workspace):
        super().__init__(workspace, "read", self.read.__doc__)
        self.func = self.read
        self.params = BaseTool.extract_params(self.read)

    @BaseTool.handle_tool_exceptions
    def read(self, file_path: str, max_lines: int = 0, encoding: str = "utf-8") -> str:
        """
        读取文件内容,可限制最大行数,返回文件内容字符串(带行号)

        Parameters
        ----------
        file_path: 文件路径
        max_lines: 最大行数(0表示不限制)
        encoding: 编码
        """
        path: Path = self.workspace.path_validator.validate(file_path)

        if not path.is_file():
            return ToolErrorResponse(self.__class__.__name__, ValueError(f"读取文件{path}时未读取到完整文件")).to_str()

        with open(path, encoding=encoding) as f:
            lines = f.readlines()

        total_lines = len(lines)

        if max_lines > 0:
            lines = lines[:max_lines]

        result_lines = []
        for i, line in enumerate(lines, 1):
            content = line.rstrip("\n\r")
            result_lines.append(f"{i:6d} | {content}")

        header = f"\n[文件: {path}]\n[行 1-{len(lines)} / 共 {total_lines} 行]\n"
        separator = "-" * 80 + "\n"

        self._record_read_meta(path)

        return header + separator + "\n".join(result_lines)
