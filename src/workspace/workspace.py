import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path

from src.models.tool_error_response import ToolErrorResponse
from src.workspace.path_validator import PathNotFoundError, PathValidator, WorkspaceBoundaryError

# 默认排除的目录 后续改为从项目配置加载
DEFAULT_EXCLUDED_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv", "dist", "build", ".idea", ".vscode"}


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
    _instance: Workspace = None

    def __new__(cls, path: str):
        if not cls._instance:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, path: str):
        if self._initialized:
            return
        self.root_path = Path(path).resolve()
        self.path_validator: PathValidator = PathValidator(self.root_path)
        self.is_git_repo: bool = (self.root_path / ".git").is_dir()
        self.platform: str = sys.platform
        self.date: str = date.today().strftime("%y-%m-%d")
        self._db = None
        self._current_session_id: int | None = None
        self._initialized = True

    @property
    def db(self):
        if self._db is None:
            from src.core.database_manager import DatabaseManager

            self._db = DatabaseManager(str(self.root_path))
        return self._db

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

            # 初始化排除目录集合
            exclude_set = set(exclude_dirs or DEFAULT_EXCLUDED_DIRS)

            # 编译正则表达式
            flags = 0 if case_sensitive else re.IGNORECASE
            try:
                regex = re.compile(pattern, flags)
            except re.error as e:
                return f"错误:正则表达式无效 - {e}"

            # 收集所有要搜索的文件(支持单文件或目录)
            files_to_search = []
            if path.is_file():
                files_to_search = [path]
            else:
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
        except UnicodeDecodeError, PermissionError:
            # 跳过无法读取的二进制文件或无权限的文件
            pass
        except Exception:
            pass

        return results

    def search_content_multi_pattern(
        self,
        patterns: list[tuple[re.Pattern, str]],
        folder_path: str = ".",
        file_pattern: str = "*",
        max_workers: int = 4,
        ignore: list[str] | None = None,
    ) -> list[dict]:
        """单次文件遍历匹配多个正则模式, 直接返回结构化数据.

        与 search_content 的区别:
        - 接受多个已编译的正则 + 类型标签, 一次遍历全部匹配
        - 返回结构化 list[dict] 而非格式化字符串, 消除下游正则解析反模式
        - 不做高亮处理(高亮是展示层关注点, 不应混入数据层)

        Args:
            patterns: [(compiled_regex, type_label), ...] 已编译正则及其类型标签
            folder_path: 搜索起始路径
            file_pattern: 文件通配符(如 "*.py")
            max_workers: 并发读取文件的线程数
            ignore: 忽略路径正则列表

        Returns:
            [{"file": str, "line_num": int, "content": str, "pattern_type": str}, ...]
            按文件路径 → 行号排序, 同一行多个模式匹配则每个各一条记录
        """
        try:
            path = self.path_validator.validate(folder_path)

            # 预编译 ignore 正则
            ignore_res: list[re.Pattern] = []
            if ignore:
                for ign in ignore:
                    try:
                        ignore_res.append(re.compile(ign))
                    except re.error:
                        continue

            # 收集文件(一次遍历)
            files_to_search: list[Path] = []
            if path.is_file():
                files_to_search = [path]
            else:
                for file_path in path.rglob(file_pattern):
                    if file_path.is_file():
                        if any(p.name in DEFAULT_EXCLUDED_DIRS for p in file_path.parents):
                            continue
                        rel = str(file_path.relative_to(self.root_path))
                        if any(ir.search(rel) for ir in ignore_res):
                            continue
                        files_to_search.append(file_path)

            if not files_to_search:
                return []

            # 并发搜索所有文件, 每个文件内一次读取、一次测试所有模式
            all_matches: list[dict] = []
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(self._search_multi_in_file, file_path, patterns): file_path
                    for file_path in files_to_search
                }
                for future in as_completed(futures):
                    try:
                        file_results = future.result()
                        if file_results:
                            all_matches.extend(file_results)
                    except Exception:
                        pass

            # 按文件路径 → 行号排序
            all_matches.sort(key=lambda m: (m["file"], m["line_num"]))
            return all_matches

        except PathNotFoundError, WorkspaceBoundaryError, PermissionError:
            return []
        except Exception:
            return []

    def _search_multi_in_file(self, file_path: Path, patterns: list[tuple[re.Pattern, str]]) -> list[dict]:
        """在单个文件中一次读取、逐行测试所有模式.

        Args:
            file_path: 文件绝对路径
            patterns: [(compiled_regex, type_label), ...]

        Returns:
            匹配项列表, 同一行多个模式匹配时每个各返回一条
        """
        results: list[dict] = []
        relative_path = str(file_path.relative_to(self.root_path))

        try:
            with open(file_path, encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    stripped = line.rstrip("\n\r")
                    for regex, pattern_type in patterns:
                        if regex.search(stripped):
                            results.append(
                                {
                                    "file": relative_path,
                                    "line_num": line_num,
                                    "content": stripped,
                                    "pattern_type": pattern_type,
                                }
                            )
        except UnicodeDecodeError, PermissionError:
            pass
        except Exception:
            pass

        return results
