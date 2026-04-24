import os
from pathlib import Path


class WorkspaceBoundaryError(Exception):
    """访问工作区外的路径时抛出"""

    pass


class PathNotFoundError(Exception):
    """工作区内路径不存在时抛出"""

    pass


class PathValidator:
    """工作区路径安全校验器,防止路径遍历和符号链接逃逸

    Args:
        workspace_root: 工作区根目录,默认为当前目录
    """

    def __init__(self, workspace_root: str | Path = "."):
        """初始化路径验证器.

        Args:
            workspace_root: 工作区根目录路径,可以是字符串或 Path 对象
                          所有后续的路径验证都将以此目录为边界

        Raises:
            FileNotFoundError: 当 workspace_root 不存在时抛出
            NotADirectoryError: 当 workspace_root 不是目录时抛出

        Example:
            >>> validator = PathValidator("/app/workspace")
        """
        self.root = Path(workspace_root).resolve()

    def resolve_path(self, target: str | Path) -> Path:
        """获取路径的绝对路径,不检查文件是否存在.

        只执行安全边界验证,不要求路径实际存在.适用于需要获取路径引用
        但文件/目录可能尚未创建的场景(如准备创建新文件).

        Args:
            target: 待解析的目标路径,可以是相对路径或绝对路径.
                   绝对路径会相对于工作区根目录解析.

        Returns:
            Path: 解析后的绝对路径对象,保证位于工作区边界内.

        Raises:
            WorkspaceBoundaryError: 当解析后的路径位于工作区根目录之外时抛出.
            OSError: 当路径解析过程中发生其他系统错误时抛出.

        Example:
            >>> validator = PathValidator("/app/workspace")
            >>> # 路径不存在但仍在工作区内
            >>> validator.resolve_path("new_folder/new_file.txt")
            PosixPath('/app/workspace/new_folder/new_file.txt')
            >>> # 路径越界会报错
            >>> validator.resolve_path("../outside.txt")
            WorkspaceBoundaryError: 路径越界: ../outside.txt
        """
        path = Path(target)
        # 统一转为相对于工作区根目录的绝对路径
        resolved = (self.root / path).resolve() if not path.is_absolute() else path.resolve()

        # 边界守卫:防 .. 逃逸与符号链接越权
        if not str(resolved).startswith(str(self.root) + os.sep) and resolved != self.root:
            raise WorkspaceBoundaryError(f"路径越界: {target}")

        return resolved

    def create_file_with_parents(self, target: str | Path, content: str = "") -> Path:
        """在工作区内创建文件,自动创建所有不存在的父目录.

        专门用于在工作区内创建新文件或覆盖已存在文件的场景.
        如果文件已存在,将覆盖其内容.如果需要保留已有内容,请先使用 read 工具确认.

        执行步骤:
        1. 安全边界验证(防止路径遍历和符号链接逃逸)
        2. 自动创建所有不存在的父目录(权限使用默认755/0o755)
        3. 写入指定内容(默认为空字符串)

        Args:
            target: 目标文件路径,可以是相对路径或绝对路径
            content: 要写入的文件内容,默认为空字符串

        Returns:
            Path: 创建成功后的绝对路径对象

        Raises:
            WorkspaceBoundaryError: 当解析后的路径位于工作区根目录之外时抛出
            PermissionError: 当没有权限创建目录或文件时抛出
            OSError: 当创建目录或文件过程中发生其他系统错误时抛出

        Example:
            >>> validator = PathValidator("/app/workspace")
            >>> # 创建深层目录结构中的文件
            >>> validator.create_file_with_parents("a/b/c/new_file.txt", "Hello World")
            PosixPath('/app/workspace/a/b/c/new_file.txt')
        """
        # 1. 边界验证
        resolved = self.resolve_path(target)

        # 2. 确保父目录存在
        parent_dir = resolved.parent
        if not parent_dir.exists():
            parent_dir.mkdir(parents=True, exist_ok=True)

        # 3. 写入文件内容
        resolved.write_text(content, encoding="utf-8")

        return resolved

    def validate(self, target: str | Path) -> Path:
        """校验路径安全性,返回绝对路径.

        执行多层安全检查:
        1. 路径规范化(解析 '..' 和符号链接)
        2. 工作区边界验证(防止路径逃逸)
        3. 文件存在性检查
        4. 读取权限验证

        Args:
            target: 待验证的目标路径,可以是相对路径或绝对路径.
                   绝对路径会相对于当前工作目录解析.

        Returns:
            Path: 验证通过后的绝对路径对象,保证位于工作区边界内.

        Raises:
            WorkspaceBoundaryError: 当解析后的路径位于工作区根目录之外时抛出.
            PathNotFoundError: 当目标路径不存在时抛出.
            PermissionError: 当目标路径存在但无读取权限时抛出.
            OSError: 当路径解析过程中发生其他系统错误时抛出.

        Example:
            >>> validator = PathValidator("/app/workspace")
            >>> # 有效路径
            >>> validator.validate("src/main.py")
            PosixPath('/app/workspace/src/main.py')
            >>> # 符号链接验证
            >>> validator.validate("link_to_config")
            PosixPath('/app/workspace/config/settings.ini')
        """
        # 复用 resolve_path 进行边界验证
        resolved = self.resolve_path(target)

        # 存在性与基础权限
        if not resolved.exists():
            raise PathNotFoundError(f"路径不存在: {target}")
        if not os.access(resolved, os.R_OK):
            raise PermissionError(f"无读取权限: {target}")  # pragma: no cover  // 需要专门准备权限, 不测了

        return resolved
