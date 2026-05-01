import contextlib
import re
from pathlib import Path

from src.models.tool_error_response import ToolErrorResponse
from src.workspace.tools.base_tool import BaseTool
from src.workspace.workspace import Workspace


def _search_in_file(lines: list[str], regex: re.Pattern, context: int) -> list[dict]:
    """在文件行中搜索匹配"""
    matches = []
    line_count = len(lines)

    for i, line in enumerate(lines):
        if regex.search(line):
            # 计算上下文行范围
            start_line = max(0, i - context)
            end_line = min(line_count, i + context + 1)

            # 收集上下文行
            context_lines = []
            for j in range(start_line, end_line):
                is_match = j == i
                context_lines.append({"line_num": j + 1, "content": lines[j].rstrip("\n\r"), "is_match": is_match})

            matches.append({"line_num": i + 1, "content": line.rstrip("\n\r"), "context": context_lines})

    return matches


def _format_regex_results(results: list[dict], pattern: str, limit: int, file_count: int) -> str:
    """格式化正则搜索结果"""
    if not results:
        return f"未找到匹配正则表达式 '{pattern}' 的内容"

    total_matches = sum(len(r["matches"]) for r in results)
    truncated = total_matches > limit

    output = [f"正则表达式搜索: '{pattern}'", f"匹配文件数: {file_count}, 匹配项数: {min(total_matches, limit)}"]

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

            if "context" in match:
                output.append(f"第 {match['line_num']} 行匹配:")
                for ctx_line in match["context"]:
                    # 增强包裹标记:匹配行用 >>> 和 <<< 包裹
                    if ctx_line["is_match"]:
                        # 提取匹配的具体内容并用标记包裹
                        content = ctx_line["content"]
                        # 使用正则找到实际匹配的部分并包裹
                        try:
                            regex = re.compile(pattern)
                            # 找到所有匹配位置并添加标记
                            matches_positions = list(regex.finditer(content))
                            if matches_positions:
                                # 从后往前插入标记,避免位置偏移
                                result_parts = []
                                last_pos = 0
                                for m in matches_positions:
                                    result_parts.append(content[last_pos : m.start()])
                                    result_parts.append(f">>>{m.group()}<<<")
                                    last_pos = m.end()
                                result_parts.append(content[last_pos:])
                                marked_content = "".join(result_parts)
                            else:
                                marked_content = f">>>{content}<<<"
                        except re.error:
                            marked_content = f">>>{content}<<<"

                        output.append(f" >>> L{ctx_line['line_num']:4d}: {marked_content}")
                    else:
                        output.append(f"     L{ctx_line['line_num']:4d}: {ctx_line['content']}")
            else:
                # 旧格式兼容
                output.append(f"  第 {match['line_num']:4d} 行: >>>{match['content']}<<<")
            output.append("")
            displayed_matches += 1

    return "\n".join(output)


class RegexSearchTool(BaseTool):
    """正则表达式搜索工具"""

    def __init__(self, workspace: Workspace):
        super().__init__(workspace, "regex_search", self.regex_search.__doc__)
        self.func = self.regex_search
        self.params = BaseTool.extract_params(self.regex_search)

    @BaseTool.handle_tool_exceptions
    def regex_search(
        self,
        pattern: str,
        path: str = ".",
        context: int = 3,
        file_pattern: str = "*",
        limit: int = 256,
        ignore: list[str] | None = None,
    ) -> str:
        """
        使用正则表达式搜索文件内容, 支持上下文显示、文件过滤和忽略路径, 返回匹配详情; 适合代码与文档探索

        Parameters
        ----------
        pattern: 正则表达式模式
        path: 搜索路径,默认为当前目录
        context: 显示匹配行的上下文行数,默认为3
        file_pattern: 文件匹配模式,支持通配符,默认为"*"
        limit: 最大匹配数量限制,默认为256
        ignore: 忽略匹配正则的文件或文件夹列表
        """
        # 验证搜索路径
        search_path: Path = self.workspace.path_validator.validate(path)

        # 编译正则表达式
        try:
            regex = re.compile(pattern)
        except re.error as e:
            return ToolErrorResponse(self.__class__.__name__, f"无效的正则表达式: {e}").to_str()

        # 收集忽略模式
        ignore_patterns = []
        if ignore:
            for ignore_pattern in ignore:
                with contextlib.suppress(re.error):
                    ignore_patterns.append(re.compile(ignore_pattern))

        # 搜索结果
        results = []
        file_count = 0

        # 遍历文件
        for file_path in search_path.rglob(file_pattern):
            # 检查是否达到限制
            if len(results) >= limit:
                break

            # 检查是否应该忽略该文件或文件夹
            should_ignore = False
            relative_path = file_path.relative_to(search_path)

            for ignore_pattern in ignore_patterns:
                # 检查是否匹配忽略模式
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
                file_results = _search_in_file(lines, regex, context)

                if file_results:
                    results.append({"file": str(file_path), "matches": file_results})
                    file_count += 1

            except OSError, UnicodeDecodeError, PermissionError:
                continue  # 跳过无法读取的文件

        # 格式化输出
        return _format_regex_results(results, pattern, limit, file_count)
