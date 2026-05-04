import contextlib
import re
from pathlib import Path

from src.workspace.tools.base_tool import BaseTool
from src.workspace.workspace import Workspace


def _search_exact_in_file(lines: list[str], search_string: str, case_sensitive: bool, whole_word: bool) -> list[dict]:
    """在文件中精确搜索"""
    matches = []

    for i, line in enumerate(lines):
        line_content = line if case_sensitive else line.lower()

        if whole_word:
            # 全词匹配:使用正则表达式
            if case_sensitive:
                word_pattern = re.compile(r"\b" + re.escape(search_string) + r"\b")
            else:
                word_pattern = re.compile(r"\b" + re.escape(search_string) + r"\b", re.IGNORECASE)

            if word_pattern.search(line_content):
                matches.append({"line_num": i + 1, "content": line.rstrip("\n\r")})
        else:
            # 简单包含匹配
            if search_string in line_content:
                matches.append({"line_num": i + 1, "content": line.rstrip("\n\r")})

    return matches


def _format_exact_results(
    results: list[dict], pattern: str, limit: int, file_count: int, case_sensitive: bool, whole_word: bool
) -> str:
    """格式化精确搜索结果"""
    if not results:
        return f"未找到匹配字符串 '{pattern}' 的内容"

    total_matches = sum(len(r["matches"]) for r in results)
    truncated = total_matches > limit

    output = [
        f"精确搜索: '{pattern}'",
        f"大小写敏感: {'是' if case_sensitive else '否'}, 全词匹配: {'是' if whole_word else '否'}",
        f"匹配文件数: {file_count}, 匹配项数: {min(total_matches, limit)}",
    ]

    if truncated:
        output.append(f"⚠️ 结果已截断,仅显示前 {limit} 个匹配项(实际共 {total_matches} 个)")

    output.append("=" * 60)

    displayed_matches = 0
    for file_result in results:
        if displayed_matches >= limit:
            break

        output.append(f"\n文件: {file_result['file']}")
        output.append("-" * 40)

        for match in file_result["matches"]:
            if displayed_matches >= limit:
                output.append(f"\n... 以及 {total_matches - limit} 个未显示的匹配项")
                break
            output.append(f"  第 {match['line_num']:4d} 行: {match['content']}")
            displayed_matches += 1

    return "\n".join(output)


class ExactSearchTool(BaseTool):
    """精确搜索工具,用于安全审计"""

    def __init__(self, workspace: Workspace):
        super().__init__(workspace, "exact_search", self.exact_search.__doc__)
        self.func = self.exact_search
        self.params = BaseTool.extract_params(self.exact_search)

    @BaseTool.handle_tool_exceptions
    def exact_search(
        self,
        pattern: str,
        path: str = ".",
        case_sensitive: bool = True,
        whole_word: bool = True,
        limit: int = 256,
        ignore: list[str] | None = None,
    ) -> str:
        """
        精确搜索字符串(支持大小写敏感/全词匹配)

        Args:
            pattern: 搜索字符串
            path: 搜索路径,默认为当前目录
            case_sensitive: 是否大小写敏感,默认为True
            whole_word: 是否全词匹配,默认为True
            limit: 最大匹配数量限制,默认为256
            ignore: 忽略匹配正则的文件或文件夹列表

        Returns:
            格式化的搜索结果字符串
        """
        # 验证搜索路径
        search_path: Path = self.workspace.path_validator.validate(path)

        # 准备搜索字符串
        search_string = pattern if case_sensitive else pattern.lower()

        # 收集忽略模式
        ignore_patterns = []
        if ignore:
            for ignore_pattern in ignore:
                with contextlib.suppress(re.error):
                    ignore_patterns.append(re.compile(ignore_pattern))

        # 搜索结果
        results = []
        file_count = 0

        # 确定要搜索的文件列表(支持单文件或目录)
        files_to_search = [search_path] if search_path.is_file() else list(search_path.rglob("*"))

        # 遍历所有文件
        for file_path in files_to_search:
            if not file_path.is_file():
                continue
            # 检查是否达到限制
            if len(results) >= limit:
                break

            # 检查是否应该忽略
            should_ignore = False
            relative_path = file_path.relative_to(search_path) if search_path.is_dir() else file_path

            for ignore_pattern in ignore_patterns:
                if ignore_pattern.search(str(relative_path)):
                    should_ignore = True
                    break

            if should_ignore:
                continue

            try:
                # 读取文件内容
                with open(file_path, encoding="utf-8") as f:
                    lines = f.readlines()

                # 搜索匹配行
                file_matches = _search_exact_in_file(lines, search_string, case_sensitive, whole_word)

                if file_matches:
                    results.append({"file": str(file_path), "matches": file_matches})
                    file_count += 1

            except OSError, UnicodeDecodeError, PermissionError:
                continue  # 跳过无法读取的文件

        # 格式化输出
        return _format_exact_results(results, pattern, limit, file_count, case_sensitive, whole_word)
