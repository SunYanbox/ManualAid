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

    def read_file(self, file_path: str, encoding="utf-8") -> str:
        """读取工作区内指定文件的全部内容,返回字符串.失败时返回错误描述."""
        try:
            path: Path = self.path_validator.validate(file_path)
            with open(path, encoding=encoding) as f:
                content: str = f.read()
            return content
        except PathNotFoundError as err1:
            return ToolErrorResponse(self.read_file.__name__, err1).to_str()
        except WorkspaceBoundaryError as err2:
            return ToolErrorResponse(self.read_file.__name__, err2).to_str()
        except PermissionError as err3:
            return ToolErrorResponse(self.read_file.__name__, err3).to_str()
        except Exception as err:
            return ToolErrorResponse(self.read_file.__name__, err).to_str()

    def ls(self, folder_path: str = ".") -> list[str] | str:
        """列出工作区内指定目录下的文件和文件夹,带[Folder]/[File]标记.失败时返回错误字符串"""
        try:
            path: Path = self.path_validator.validate(folder_path)
            if not path.is_dir():
                raise ValueError(f"{path} is not a directory")
            return [
                f"{'[Folder]' if item.is_dir() else '[File]'} {item.relative_to(self.root_path)}"
                for item in path.iterdir()
            ]
        except PathNotFoundError as err1:
            return ToolErrorResponse(self.ls.__name__, err1).to_str()
        except WorkspaceBoundaryError as err2:
            return ToolErrorResponse(self.ls.__name__, err2).to_str()
        except PermissionError as err3:
            return ToolErrorResponse(self.ls.__name__, err3).to_str()
        except Exception as err:
            return ToolErrorResponse(self.ls.__name__, err).to_str()

    def glob(self, pattern: str) -> list[str] | str:
        """在工作区内按通配符模式匹配并列出所有路径,带类型标记.失败时返回错误字符串"""
        try:
            return [
                f"{'[Folder]' if item.is_dir() else '[File]'} {item.relative_to(self.root_path)}"
                for item in self.root_path.glob(pattern)
            ]
        except PathNotFoundError as err1:
            return ToolErrorResponse(self.glob.__name__, err1).to_str()
        except WorkspaceBoundaryError as err2:
            return ToolErrorResponse(self.glob.__name__, err2).to_str()
        except PermissionError as err3:
            return ToolErrorResponse(self.glob.__name__, err3).to_str()
        except Exception as err:
            return ToolErrorResponse(self.glob.__name__, err).to_str()

    def read_file_lines(
        self, file_path: str, start_line: int = 1, end_line: int | None = None, encoding: str = "utf-8"
    ) -> str:
        """读取工作区内文件的指定行范围(行号从1开始),返回带行号和文件头格式的内容.失败时返回错误信息"""
        try:
            path = self.path_validator.validate(file_path)

            if not path.is_file():
                return ToolErrorResponse(self.read_file_lines.__name__, ValueError(f"{path} is not a file")).to_str()

            with open(path, encoding=encoding) as f:
                lines = f.readlines()

            total_lines = len(lines)

            # 验证行号
            if start_line < 1:
                start_line = 1
            if start_line > total_lines:
                return f"错误:起始行 {start_line} 超过文件总行数 ({total_lines})"

            end_line = total_lines if end_line is None else min(end_line, total_lines)

            if end_line < start_line:
                return f"错误:结束行 {end_line} 小于起始行 {start_line}"

            # 提取并格式化行内容
            result_lines = []
            for i in range(start_line - 1, end_line):
                line_num = i + 1
                content = lines[i].rstrip("\n\r")
                result_lines.append(f"{line_num:6d} | {content}")

            header = f"\n[文件: {file_path}]\n[行 {start_line}-{end_line} / 共 {total_lines} 行]\n"
            separator = "-" * 80 + "\n"

            return header + separator + "\n".join(result_lines)

        except PathNotFoundError as err1:
            return ToolErrorResponse(self.read_file_lines.__name__, err1).to_str()
        except WorkspaceBoundaryError as err2:
            return ToolErrorResponse(self.read_file_lines.__name__, err2).to_str()
        except PermissionError as err3:
            return ToolErrorResponse(self.read_file_lines.__name__, err3).to_str()
        except Exception as err:
            return ToolErrorResponse(self.read_file_lines.__name__, err).to_str()

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

    def write(self, file_path: str, old_str: str, new_str: str, encoding: str = "utf-8",
              start_line: int = None, end_line: int = None) -> str:
        """在工作区文件中精确替换字符串，支持通过start_line/end_line参数限制替换行范围(行号从1开始)，
返回替换次数或详细错误指导；当文件不存在时自动创建文件，
替换失败时会提示使用read_file/read_file_lines重新确认内容。"""
        try:
            path = self.path_validator.validate(file_path, create_file_if_not_exist=True)

            if not path.is_file():
                return ToolErrorResponse(self.write.__name__, ValueError(f"{path} is not a file")).to_str()

            # 读取原始内容
            with open(path, encoding=encoding) as f:
                original_content = f.read()

            # 处理行范围限制
            if start_line is not None or end_line is not None:
                lines = original_content.splitlines(keepends=True)
                total_lines = len(lines)

                # 验证行号范围
                if start_line is None:
                    start_line = 1
                if end_line is None:
                    end_line = total_lines

                # 检查行号有效性
                invalid_lines = []
                if start_line < 1:
                    invalid_lines.append(f"起始行 {start_line} < 1")
                if end_line > total_lines:
                    invalid_lines.append(f"结束行 {end_line} > 总行数 {total_lines}")
                if start_line > end_line:
                    invalid_lines.append(f"起始行 {start_line} > 结束行 {end_line}")

                if invalid_lines:
                    error_msg = (
                        f"错误:行范围无效 - {', '.join(invalid_lines)}\n"
                        f"文件总行数: {total_lines}\n"
                        f"请调整行范围后重试"
                    )
                    return error_msg

                # 提取指定行范围的内容
                target_lines = lines[start_line - 1:end_line]
                target_content = ''.join(target_lines)

                # 在目标范围内搜索要替换的字符串
                if old_str not in target_content:
                    # 显示行范围信息
                    range_info = f"行 {start_line}-{end_line}" if start_line != end_line else f"行 {start_line}"
                    error_msg = (
                        f"错误:在文件的 {range_info} 中未找到要替换的字符串\n"
                        f"原字符串: '{old_str[:200]}{'...' if len(old_str) > 200 else ''}'\n\n"
                        f"请执行以下步骤:\n"
                        f"1. 使用 read_file_lines 工具读取文件 '{file_path}' 的行 {start_line}-{end_line} 确认内容\n"
                        f"2. 确认要替换的字符串精确匹配(包括空格、换行符等)\n"
                        f"3. 如需要更大范围,请调整 start_line/end_line 参数(当前范围: {start_line}-{end_line})\n"
                        f"4. 如不需要行限制,请省略 start_line 和 end_line 参数\n"
                        f"5. 然后重新调用 write 工具进行替换"
                    )
                    return error_msg

                # 只替换指定行范围内的内容
                new_target_content = target_content.replace(old_str, new_str)
                count = target_content.count(old_str)

                # 重新组装文件内容
                new_lines = lines[:start_line - 1] + [new_target_content] + lines[end_line:]
                new_content = ''.join(new_lines)

            else:
                # 没有行范围限制,全局替换
                if old_str not in original_content:
                    error_msg = (
                        f"错误:在文件 '{file_path}' 中未找到要替换的字符串\n"
                        f"原字符串: '{old_str[:200]}{'...' if len(old_str) > 200 else ''}'\n\n"
                        f"请执行以下步骤:\n"
                        f"1. 使用 read_file 工具重新读取文件 '{file_path}' 确认当前内容\n"
                        f"2. 确认要替换的字符串精确匹配(包括空格、换行符等)\n"
                        f"3. 如果需要部分匹配,请先读取文件内容确认完整字符串\n"
                        f"4. 然后重新调用 write 工具进行替换"
                    )
                    return error_msg

                new_content = original_content.replace(old_str, new_str)
                count = original_content.count(old_str)

            # 检查内容是否变化
            with open(path, encoding=encoding) as f:
                current_content = f.read()

            if new_content == current_content:
                range_info = f" (行 {start_line}-{end_line})" if start_line is not None or end_line is not None else ""
                return f"警告:替换后内容未发生变化{range_info},请确认 old_str 和 new_str 是否相同"

            # 写入文件
            with open(path, encoding=encoding, mode="w") as f:
                f.write(new_content)

            # 构建返回信息
            range_info = f" (行 {start_line}-{end_line})" if start_line is not None or end_line is not None else ""
            if start_line is not None and end_line is not None and start_line == end_line:
                range_info = f" (第 {start_line} 行)"

            return (
                f"成功:已替换文件 '{file_path}' 中的 {count} 处匹配{range_info}\n"
                f"原字符串长度: {len(old_str)} 字符\n"
                f"新字符串长度: {len(new_str)} 字符"
            )

        except PathNotFoundError as err1:
            return ToolErrorResponse(self.write.__name__, err1).to_str()
        except WorkspaceBoundaryError as err2:
            return ToolErrorResponse(self.write.__name__, err2).to_str()
        except PermissionError as err3:
            return ToolErrorResponse(self.write.__name__, err3).to_str()
        except Exception as err:
            return ToolErrorResponse(self.write.__name__, err).to_str()

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
