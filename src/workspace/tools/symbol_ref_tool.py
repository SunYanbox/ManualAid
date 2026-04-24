"""符号引用查找工具 - 查找函数、类、变量等的定义和引用"""

import contextlib
import re
from pathlib import Path

from src.core.tool_error_response import ToolErrorResponse
from src.workspace.path_validator import PathNotFoundError, WorkspaceBoundaryError
from src.workspace.tools.base_tool import BaseTool
from src.workspace.workspace import Workspace


# noinspection SpellCheckingInspection
def _generate_patterns(symbol_name: str, language: str, include_def: bool, include_ref: bool) -> list[dict[str, str]]:
    """根据语言生成搜索模式"""
    patterns = []

    # 转义特殊字符
    escaped_name = re.escape(symbol_name)

    if language == "python":
        if include_def:
            # 函数定义: def func_name(
            patterns.append({"pattern": rf"^\s*def\s+{escaped_name}\s*\(", "type": "definition_function"})
            # 类定义: class ClassName:
            patterns.append({"pattern": rf"^\s*class\s+{escaped_name}\s*[:\(]", "type": "definition_class"})
            # 变量/属性定义
            patterns.append({"pattern": rf"^\s*{escaped_name}\s*=", "type": "definition_variable"})
            # 方法定义
            patterns.append({"pattern": rf"^\s*def\s+{escaped_name}\s*\(self", "type": "definition_method"})

        if include_ref:
            # 函数调用: func_name(
            patterns.append({"pattern": rf"{escaped_name}\s*\(", "type": "reference_call"})
            # 类实例化: ClassName(
            patterns.append({"pattern": rf"{escaped_name}\s*\(", "type": "reference_instantiation"})
            # 属性访问: .symbol_name 或 symbol_name.
            patterns.append({"pattern": rf"\.{escaped_name}\b|\b{escaped_name}\.", "type": "reference_attribute"})
            # 导入语句: from module import symbol_name
            patterns.append(
                {
                    "pattern": rf"\bimport\s+.*\b{escaped_name}\b|\bfrom\s+.*\s+import\s+.*\b{escaped_name}\b",
                    "type": "reference_import",
                }
            )

    elif language in ["javascript", "typescript"]:
        if include_def:
            # 函数定义: function func_name() 或 const func_name =
            patterns.append(
                {
                    "pattern": (
                        rf"(function\s+{escaped_name}\s*\(|const\s+{escaped_name}\s*="
                        rf"\s*(function|\()|let\s+{escaped_name}\s*=\s*(function|\())"
                    ),
                    "type": "definition_function",
                }
            )
            # 类定义: class ClassName
            patterns.append(
                {
                    "pattern": rf"class\s+{escaped_name}\s*\{{|class\s+{escaped_name}\s+extends",
                    "type": "definition_class",
                }
            )
            # 变量定义: const/let/var symbol_name =
            patterns.append({"pattern": rf"\b(const|let|var)\s+{escaped_name}\s*=", "type": "definition_variable"})
            # 导出定义: export ...
            patterns.append({"pattern": rf"export\s+.*\b{escaped_name}\b", "type": "definition_export"})

        if include_ref:
            # 函数调用/方法调用
            patterns.append({"pattern": rf"{escaped_name}\s*\(", "type": "reference_call"})
            # 属性访问
            patterns.append({"pattern": rf"\.{escaped_name}\b|\b{escaped_name}\.", "type": "reference_property"})
            # 导入语句
            patterns.append(
                {
                    "pattern": (
                        rf"import\s+.*\b{escaped_name}\b|import\s+\{{\s*.*\b{escaped_name}"
                        rf"\b.*\s*\}}|require\s*\(.*\b{escaped_name}\b"
                    ),
                    "type": "reference_import",
                }
            )

    elif language == "markdown":
        # Markdown 中的标题、链接、代码块引用
        if include_def:
            patterns.append({"pattern": rf"^#+\s+.*\b{escaped_name}\b", "type": "definition_heading"})
        if include_ref:
            patterns.append(
                {
                    "pattern": rf"\[{escaped_name}\]\(|\[{escaped_name}\]\[|\[{escaped_name}\]\:|`{escaped_name}`",
                    "type": "reference_link_or_code",
                }
            )

    else:  # general
        # 通用模式: 作为独立单词出现
        patterns.append({"pattern": rf"\b{escaped_name}\b", "type": "general_reference"})

    # 去重: 根据pattern去重
    unique_patterns = []
    seen = set()
    for p in patterns:
        if p["pattern"] not in seen:
            seen.add(p["pattern"])
            unique_patterns.append(p)

    return unique_patterns


def _search_pattern(
    search_path: Path,
    pattern: str,
    match_type: str,
    symbol_name: str,
    context_lines: int,
    limit: int,
    ignore: list[str] | None,
) -> list[dict]:
    """执行单个模式的搜索"""
    results = []

    try:
        regex = re.compile(pattern, re.IGNORECASE)
    except re.error:
        return results

    # 编译忽略模式
    ignore_patterns = []
    if ignore:
        for ignore_pattern in ignore:
            with contextlib.suppress(re.error):
                ignore_patterns.append(re.compile(ignore_pattern))

    # 遍历文件
    for file_path in search_path.rglob("*"):
        if len(results) >= limit:
            break

        if not file_path.is_file():
            continue

        # 检查是否应该忽略
        should_ignore = False
        try:
            relative_path = file_path.relative_to(search_path)
            for ignore_pattern in ignore_patterns:
                if ignore_pattern.search(str(relative_path)):
                    should_ignore = True
                    break
        except ValueError:
            should_ignore = True

        if should_ignore:
            continue

        # 读取文件内容
        try:
            with open(file_path, encoding="utf-8") as f:
                lines = f.readlines()
        except (UnicodeDecodeError, PermissionError, OSError):
            continue

        # 搜索匹配
        file_matches = []
        for i, line in enumerate(lines):
            if regex.search(line):
                # 收集上下文
                start_line = max(0, i - context_lines)
                end_line = min(len(lines), i + context_lines + 1)

                context_data = []
                for j in range(start_line, end_line):
                    context_data.append({"line_num": j + 1, "content": lines[j].rstrip("\n\r"), "is_match": j == i})

                file_matches.append(
                    {
                        "line_num": i + 1,
                        "content": line.rstrip("\n\r"),
                        "context": context_data,
                        "match_type": match_type,
                        "symbol_name": symbol_name,  # 使用 symbol_name 参数
                    }
                )

                if len(file_matches) >= 10:  # 每个文件最多10个匹配
                    break

        if file_matches:
            results.append({"file": str(file_path), "matches": file_matches, "type": match_type})

    return results


# noinspection SpellCheckingInspection
def _detect_language(search_path: Path, specified_lang: str) -> str:
    """检测项目的主要语言"""
    if specified_lang != "auto":
        return specified_lang

    # 检查项目文件
    lang_indicators = {
        "python": ["*.py", "requirements.txt", "pyproject.toml", "setup.py"],
        "javascript": ["*.js", "package.json", "*.jsx"],
        "typescript": ["*.ts", "*.tsx", "tsconfig.json"],
        "markdown": ["*.md", "*.markdown"],
    }

    lang_scores = {lang: 0 for lang in lang_indicators}

    for lang, patterns in lang_indicators.items():
        for pattern in patterns:
            matches = list(search_path.rglob(pattern))
            lang_scores[lang] += len(matches)

    # 选择得分最高的语言
    if max(lang_scores.values()) > 0:
        return max(lang_scores, key=lang_scores.get)

    return "general"


def _get_type_label(match_type: str) -> str:
    """获取匹配类型的友好标签"""
    labels = {
        "definition_function": "函数定义",
        "definition_class": "类定义",
        "definition_method": "方法定义",
        "definition_variable": "变量定义",
        "definition_export": "导出定义",
        "definition_heading": "标题定义",
        "reference_call": "函数/方法调用",
        "reference_instantiation": "实例化",
        "reference_attribute": "属性访问",
        "reference_import": "导入引用",
        "reference_property": "属性访问",
        "reference_link_or_code": "链接或代码引用",
        "general_reference": "通用引用",
    }
    return labels.get(match_type, f"{match_type}")


def _format_results(results: list[dict], symbol_name: str, language: str, limit: int) -> str:
    """格式化搜索结果"""
    if not results:
        return (
            f"未找到符号 '{symbol_name}' 的定义或引用"
            f"(语言: {language})\n\n提示: 可以尝试指定不同的语言类型或调整搜索路径"
        )

    total_matches = sum(len(r["matches"]) for r in results)
    truncated = total_matches > limit

    output = [
        f"符号引用查找: '{symbol_name}'",
        f"语言: {language}",
        f"匹配文件数: {len(results)}, 匹配项数: {min(total_matches, limit)}",
    ]

    if truncated:
        output.append(f"[WARN] 结果已截断,仅显示前 {limit} 个匹配项(实际共 {total_matches} 个)")

    output.append("=" * 80)

    displayed_matches = 0
    for file_result in results:
        if displayed_matches >= limit:
            break

        output.append(f"\n文件: {file_result['file']}")
        output.append(f"匹配类型: {file_result['type']}")
        output.append("-" * 80)

        for match in file_result["matches"]:
            if displayed_matches >= limit:
                output.append(f"\n... 以及 {total_matches - limit} 个未显示的匹配项")
                break

            # 类型标签
            type_label = _get_type_label(match["match_type"])
            output.append(f"{type_label} 第 {match['line_num']} 行:")

            # 显示上下文
            for ctx_line in match["context"]:
                prefix = ">>>" if ctx_line["is_match"] else "   "
                output.append(f"  {prefix} L{ctx_line['line_num']:4d}: {ctx_line['content']}")

            output.append("")  # 空行分隔
            displayed_matches += 1

    return "\n".join(output)


class SymbolRefTool(BaseTool):
    """查找符号引用工具 - 定位函数、类、变量等的定义和引用位置"""

    def __init__(self, workspace: Workspace):
        super().__init__(workspace, "symbol_ref", self.symbol_ref.__doc__, read_permission=True, write_permission=False)
        self.func = self.symbol_ref
        self.params = BaseTool.extract_params(self.symbol_ref)

    def symbol_ref(
        self,
        symbol_name: str,
        path: str = ".",
        language: str = "auto",
        include_definitions: bool = True,
        include_references: bool = True,
        context_lines: int = 2,
        limit: int = 256,
        ignore: list[str] | None = None,
    ) -> str:
        """
        查找符号(函数、类、变量等)的定义和引用位置

        支持自动识别语言类型,生成智能搜索模式来定位符号的定义和所有使用位置.
        适用于代码探索、重构影响分析、理解代码结构等场景.

        Args:
            symbol_name: 要查找的符号名称(如函数名、类名、变量名)
            path: 搜索路径,默认为当前目录
            language: 语言类型(auto/python/javascript/typescript/markdown/general),默认auto
            include_definitions: 是否包含定义位置,默认True
            include_references: 是否包含引用位置,默认True
            context_lines: 显示匹配行的上下文行数,默认2
            limit: 最大匹配数量限制,默认为256
            ignore: 忽略匹配正则的文件或文件夹列表

        Returns:
            格式化的符号引用搜索结果
        """
        try:
            # 验证搜索路径
            search_path: Path = self.workspace.path_validator.validate(path)
            if not search_path.exists():
                return ToolErrorResponse(self.__class__.__name__, f"路径不存在: {path}").to_str()

            # 自动检测语言
            detected_lang = _detect_language(search_path, language)

            # 生成搜索模式
            patterns = _generate_patterns(symbol_name, detected_lang, include_definitions, include_references)

            if not patterns:
                return f"无法为符号 '{symbol_name}' 生成有效的搜索模式(语言: {detected_lang})"

            # 执行搜索
            all_results = []
            for pattern_info in patterns:
                results = _search_pattern(
                    search_path,
                    pattern_info["pattern"],
                    pattern_info["type"],
                    symbol_name,
                    context_lines,
                    limit - len(all_results),
                    ignore,
                )
                all_results.extend(results)
                if len(all_results) >= limit:
                    break

            # 格式化输出
            return _format_results(all_results, symbol_name, detected_lang, limit)

        except PathNotFoundError as err1:
            return ToolErrorResponse(self.__class__.__name__, err1).to_str()
        except WorkspaceBoundaryError as err2:
            return ToolErrorResponse(self.__class__.__name__, err2).to_str()
        except Exception as err:
            return ToolErrorResponse(self.__class__.__name__, err).to_str()
