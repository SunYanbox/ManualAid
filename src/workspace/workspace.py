import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path

from src.core.tool_error_response import ToolErrorResponse
from src.workspace.path_validator import PathNotFoundError, PathValidator, WorkspaceBoundaryError


def _highlight_matches(line: str, regex: re.Pattern) -> str:
    """
    高亮显示行中的匹配部分(内部方法)

    Args:
        line: 原始行内容
        regex: 编译后的正则表达式

    Returns:
        带有 **匹配** 标记的行内容
    """

    def replacer(match):
        return f"**{match.group(0)}**"

    try:
        highlighted = regex.sub(replacer, line)
        return highlighted
    except Exception:
        return line


class Workspace:
    _instance: "Workspace" = None

    def __new__(cls, path: str):
        if not cls._instance:
            cls._instance = super().__new__(cls)
            cls._instance.__init__(path)
        return cls._instance

    def __init__(self, path: str):
        self.root_path = Path(path).resolve()
        self.path_validator: PathValidator = PathValidator(self.root_path)
        self.is_git_repo: bool = (self.root_path / ".git").is_dir()
        self.platform: str = sys.platform
        self.date: str = date.today().strftime("%y-%m-%d")

    def search_content(
        self,
        pattern: str,
        folder_path: str = ".",
        exclude_dirs: list[str] | None = None,
        file_pattern: str = "*",
        max_workers: int = 4,
        case_sensitive: bool = False,
    ) -> str:
        """在工作区内递归搜索文件内容(正则匹配),支持排除目录、并发读取和匹配高亮.返回格式化搜索结果或错误"""
        try:
            path = self.path_validator.validate(folder_path)

            if not path.is_dir():
                return ToolErrorResponse(
                    self.search_content.__name__, ValueError(f"{path} is not a directory")
                ).to_str()

            # 初始化排除目录集合
            exclude_set = set(exclude_dirs or [".git", "__pycache__", "node_modules", ".venv", "venv", "dist", "build"])

            # 编译正则表达式
            flags = 0 if case_sensitive else re.IGNORECASE
            try:
                regex = re.compile(pattern, flags)
            except re.error as e:
                return f"错误:正则表达式无效 - {e}"

            # 收集所有要搜索的文件
            files_to_search = []
            for file_path in path.rglob(file_pattern):
                if file_path.is_file():
                    # 检查是否在排除目录中
                    should_exclude = False
                    for parent in file_path.parents:
                        if parent.name in exclude_set:
                            should_exclude = True
                            break
                    if not should_exclude:
                        files_to_search.append(file_path)

            if not files_to_search:
                return f"在 {folder_path} 中没有找到匹配 {file_pattern} 的文件"

            # 异步搜索文件
            results = []
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(self._search_in_file, file_path, regex): file_path for file_path in files_to_search
                }

                for future in as_completed(futures):
                    file_path = futures[future]
                    try:
                        file_results = future.result()
                        if file_results:
                            results.extend(file_results)
                    except Exception as e:
                        results.append(f"[错误] {file_path.relative_to(self.root_path)}: {e!s}")

            # 格式化输出
            if not results:
                return f"未找到匹配 '{pattern}' 的内容"

            output_lines = [
                f"搜索模式: {pattern}",
                f"搜索路径: {folder_path}",
                f"排除目录: {', '.join(sorted(exclude_set)) if exclude_set else '无'}",
                f"文件模式: {file_pattern}",
                f"匹配文件数: {len(set(r[0] for r in results if not r[0].startswith('[错误]')))}",
                f"匹配行数: {len(results)}",
                "-" * 80,
                "",
            ]

            current_file = None
            for file_rel, line_num, line_content in results:
                if file_rel != current_file:
                    current_file = file_rel
                    output_lines.append(f"\n[文件] {current_file}")
                    output_lines.append("-" * 40)

                # 高亮显示匹配的部分
                highlighted = _highlight_matches(line_content, regex)
                output_lines.append(f"  {line_num:4d} | {highlighted}")

            return "\n".join(output_lines)

        except PathNotFoundError as err1:
            return ToolErrorResponse(self.search_content.__name__, err1).to_str()
        except WorkspaceBoundaryError as err2:
            return ToolErrorResponse(self.search_content.__name__, err2).to_str()
        except PermissionError as err3:
            return ToolErrorResponse(self.search_content.__name__, err3).to_str()
        except Exception as err:
            return ToolErrorResponse(self.search_content.__name__, err).to_str()

    def _search_in_file(self, file_path: Path, regex: re.Pattern) -> list[tuple]:
        """
        在单个文件中搜索匹配内容(内部方法)

        Returns:
            List of (relative_path, line_number, line_content)
        """
        results = []
        relative_path = str(file_path.relative_to(self.root_path))

        try:
            with open(file_path, encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    if regex.search(line):
                        results.append((relative_path, line_num, line.rstrip("\n\r")))
        except (UnicodeDecodeError, PermissionError):
            # 跳过无法读取的二进制文件或无权限的文件
            pass
        except Exception:
            pass

        return results
