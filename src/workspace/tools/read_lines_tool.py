from pathlib import Path

from src.constants.tools_docs import ReadLines_TOOL
from src.core.tool_error_response import ToolErrorResponse
from src.workspace.path_validator import PathNotFoundError, WorkspaceBoundaryError
from src.workspace.tools.base_tool import BaseTool
from src.workspace.workspace import Workspace


class ReadLinesTool(BaseTool):
    def __init__(self, workspace: Workspace):
        super().__init__(workspace, *ReadLines_TOOL)
        self.func = self.read_lines
        self.params = BaseTool.extract_params(self.read_lines)

    def read_lines(self, file_path: str, start: int, end: int, context: int = 2, encoding="utf-8") -> str:
        try:
            path: Path = self.workspace.path_validator.validate(file_path)

            if not path.is_file():
                return ToolErrorResponse(
                    self.__class__.__name__, ValueError(f"读取文件{path}时未读取到完整文件")
                ).to_str()

            with open(path, encoding=encoding) as f:
                lines = f.readlines()

            total_lines = len(lines)

            context = max(0, context)

            start -= context
            end += context

            # 验证行号
            if start < 1:
                start = 1
            if start > total_lines:
                return f"错误:起始行 {start} 超过文件总行数 ({total_lines})"

            end = total_lines if end is None else min(end, total_lines)

            if end < start:
                return f"错误:结束行 {end} 小于起始行 {start}"

            result_lines = []
            for i in range(start - 1, end):
                line_num = i + 1
                content = lines[i].rstrip("\n\r")
                result_lines.append(f"{line_num:6d} | {content}")

            header = f"\n[文件: {path}]\n[行 {start}-{end} / 共 {total_lines} 行]\n"
            separator = "-" * 80 + "\n"

            return header + separator + "\n".join(result_lines)
        except PathNotFoundError as err1:
            return ToolErrorResponse(self.__class__.__name__, err1).to_str()
        except WorkspaceBoundaryError as err2:
            return ToolErrorResponse(self.__class__.__name__, err2).to_str()
        except PermissionError as err3:
            return ToolErrorResponse(self.__class__.__name__, err3).to_str()
        except Exception as err:
            return ToolErrorResponse(self.__class__.__name__, err).to_str()
