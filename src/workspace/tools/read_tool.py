from pathlib import Path

from src.models.tool_error_response import ToolErrorResponse
from src.utils.binary_detector import is_binary_file
from src.workspace.tools.base_tool import BaseTool
from src.workspace.workspace import Workspace


def _resolve_index(idx: int, total: int) -> int:
    """Resolve a 1-based or negative index to a clamped 1-based line number."""
    if idx < 0:
        idx = total + 1 + idx
    if idx < 1:
        return 1
    if idx > total:
        return total
    return idx


class ReadTool(BaseTool):
    def __init__(self, workspace: Workspace):
        super().__init__(workspace, "read", self.read.__doc__)
        self.func = self.read
        self.params = BaseTool.extract_params(self.read)
        self.param_descriptions = {
            "path": "文件路径",
            "start": "起始行号(1开始; 负数表示倒数, -1=最后一行)",
            "end": "结束行号(1开始; 负数表示倒数, -1=最后一行)",
            "context": "扩展结果行数范围 行数范围最终为(start-context, end+context)",
            "encoding": "编码",
        }

    @BaseTool.handle_tool_exceptions
    def read(self, path: str, start: int = 1, end: int = -1, context: int = 0, encoding: str = "utf-8") -> str:
        """
        读取文件内容, 返回带行号的格式化内容
        """
        file_path: Path = self.workspace.path_validator.validate(path)

        if not file_path.is_file():
            return ToolErrorResponse(self.__class__.__name__, ValueError(f"读取文件{file_path}时未读取到完整文件")).to_str()

        if is_binary_file(file_path):
            return ToolErrorResponse(
                self.__class__.__name__,
                ValueError(f"无法读取二进制文件: {file_path}. 请使用二进制安全工具或转换为 base64."),
            ).to_str()

        with open(file_path, encoding=encoding) as f:
            lines = f.readlines()

        total_lines = len(lines)

        if total_lines == 0:
            header = f"\n[文件: {file_path}]\n[行 0-0 / 共 0 行]\n"
            separator = "-" * 80 + "\n"
            self._record_read_meta(file_path)
            return header + separator

        context = max(0, context)

        actual_start = _resolve_index(start, total_lines) - context
        actual_end = _resolve_index(end, total_lines) + context

        if actual_start < 1:
            actual_start = 1
        if actual_end > total_lines:
            actual_end = total_lines

        if actual_end < actual_start:
            return (
                f"错误:解析后的结束行 {actual_end} 小于起始行 {actual_start} "
                f"(原始参数: start={start}, end={end}, context={context})"
            )

        result_lines = []
        for i in range(actual_start - 1, actual_end):
            line_num = i + 1
            content = lines[i].rstrip("\n\r")
            result_lines.append(f"{line_num:6d} | {content}")

        header = f"\n[文件: {file_path}]\n[行 {actual_start}-{actual_end} / 共 {total_lines} 行]\n"
        separator = "-" * 80 + "\n"

        self._record_read_meta(file_path)

        return header + separator + "\n".join(result_lines)
