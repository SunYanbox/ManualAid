import stat as stat_constants
from datetime import datetime
from pathlib import Path

from src.workspace.tools.base_tool import BaseTool
from src.workspace.workspace import Workspace


class StatTool(BaseTool):
    """获取文件或目录的详细信息"""

    def __init__(self, workspace: Workspace):
        super().__init__(workspace, "stat", self.stat.__doc__)
        self.func = self.stat
        self.params = BaseTool.extract_params(self.stat)
        self.param_descriptions = {
            "path": "文件或目录路径",
        }

    @BaseTool.handle_tool_exceptions
    def stat(self, path: str = ".") -> str:
        """
        获取工作区内文件或目录的详细信息,包括大小、行数(仅文件)、修改时间、权限等
        """
        # 验证路径
        target_path: Path = self.workspace.path_validator.validate(path)

        # 获取基本 stat 信息
        path_stat = target_path.stat()

        # 构建输出
        output = [
            f"路径: {target_path.relative_to(self.workspace.root_path)}",
            f"绝对路径: {target_path.resolve()}",
            f"类型: {'目录' if target_path.is_dir() else '文件' if target_path.is_file() else '其他'}",
        ]

        # 大小信息
        size_bytes = path_stat.st_size
        if size_bytes < 1024:
            size_str = f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            size_str = f"{size_bytes / 1024:.2f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            size_str = f"{size_bytes / (1024 * 1024):.2f} MB"
        else:
            size_str = f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

        output.append(f"大小: {size_str} ({size_bytes} bytes)")

        # 行数(仅对文件有效)
        if target_path.is_file():
            try:
                with open(target_path, encoding="utf-8") as f:
                    line_count = sum(1 for _ in f)
                output.append(f"行数: {line_count}")
            except UnicodeDecodeError, PermissionError, OSError:
                output.append("行数: 无法读取(二进制文件或编码错误)")

        # 时间信息
        def format_timestamp(timestamp: float) -> str:
            dt = datetime.fromtimestamp(timestamp)
            return dt.strftime("%Y-%m-%d %H:%M:%S")

        output.append(f"创建时间: {format_timestamp(path_stat.st_ctime)}")
        output.append(f"修改时间: {format_timestamp(path_stat.st_mtime)}")
        output.append(f"访问时间: {format_timestamp(path_stat.st_atime)}")

        # 权限信息
        mode = path_stat.st_mode

        # 文件类型
        if stat_constants.S_ISDIR(mode):
            file_type = "d"
        elif stat_constants.S_ISREG(mode):
            file_type = "-"
        elif stat_constants.S_ISLNK(mode):
            file_type = "l"
        elif stat_constants.S_ISCHR(mode):
            file_type = "c"
        elif stat_constants.S_ISBLK(mode):
            file_type = "b"
        elif stat_constants.S_ISFIFO(mode):
            file_type = "p"
        elif stat_constants.S_ISSOCK(mode):
            file_type = "s"
        else:
            file_type = "?"

        # 所有者权限
        owner = (
            ("r" if mode & stat_constants.S_IRUSR else "-")
            + ("w" if mode & stat_constants.S_IWUSR else "-")
            + ("x" if mode & stat_constants.S_IXUSR else "-")
        )
        # 组权限
        group = (
            ("r" if mode & stat_constants.S_IRGRP else "-")
            + ("w" if mode & stat_constants.S_IWGRP else "-")
            + ("x" if mode & stat_constants.S_IXGRP else "-")
        )
        # 其他用户权限
        other = (
            ("r" if mode & stat_constants.S_IROTH else "-")
            + ("w" if mode & stat_constants.S_IWOTH else "-")
            + ("x" if mode & stat_constants.S_IXOTH else "-")
        )

        permissions = f"{file_type}{owner}{group}{other}"
        output.append(f"权限: {permissions}")

        # 数值权限(八进制)
        numeric_perms = oct(mode & 0o777)[2:]
        output.append(f"权限(八进制): {numeric_perms}")

        # 所有者信息
        try:
            uid = path_stat.st_uid
            gid = path_stat.st_gid
            output.append(f"所有者UID: {uid}, GID: {gid}")
        except AttributeError:
            pass  # Windows 可能没有 uid/gid

        # 链接数
        output.append(f"硬链接数: {path_stat.st_nlink}")

        # 如果是符号链接,显示目标
        if target_path.is_symlink():
            try:
                link_target = target_path.resolve()
                output.append(f"符号链接指向: {link_target}")
            except OSError:
                output.append("符号链接指向: 无法解析")

        # 如果是目录,显示子项数量
        if target_path.is_dir():
            try:
                items = list(target_path.iterdir())
                dir_count = sum(1 for item in items if item.is_dir())
                file_count = sum(1 for item in items if item.is_file())
                output.append(f"目录内容: {len(items)} 项({dir_count} 个目录, {file_count} 个文件)")
            except PermissionError:
                output.append("目录内容: 无法访问")

        return "\n".join(output)
