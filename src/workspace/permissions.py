"""统一权限决策引擎 —— 路径级细粒度权限控制.

整合现有权限机制:
1. BaseTool 的 read_permission/write_permission 布尔属性
2. PathValidator 的边界检查
3. binary_detector 的文件类型检测
4. 敏感文件保护(新增)
5. Git 工具的安全模型(白名单+拦截正则, 后续提取)
6. mtime 校验
7. 审计审批层

提供统一的 "工具 X 能否对路径 Y 执行操作 Z" 查询接口.
"""

from __future__ import annotations

from enum import Enum, auto
from pathlib import Path


class Operation(Enum):
    """权限操作类型."""

    READ = auto()
    WRITE = auto()
    SEARCH = auto()
    EXECUTE = auto()
    DELETE = auto()


class Decision(Enum):
    """权限决策结果."""

    ALLOWED = "allowed"
    DENIED = "denied"


class PermissionManager:
    """统一权限决策引擎.

    使用方式(从 Workspace 获取):
        perm = workspace.permission_manager
        if perm.is_allowed("read_tool", path, Operation.READ):
            ...

    Args:
        workspace_root: 工作区根目录
    """

    def __init__(self, workspace_root: Path):
        self._root = workspace_root

        # 敏感文件正则列表(与 ExclusionManager 保持一致)
        self._sensitive_patterns: list[str] = [
            r"\.env$",
            r"\.env\..+$",
            r".*\.pem$",
            r"credentials\..*$",
            r".*\.key$",
            r".*\.cert$",
            r"id_rsa$",
            r"id_ed25519$",
            r".*\.cred$",
            r".*\.secret$",
        ]

        # 操作 → 所需权限级别映射
        self._operation_permissions: dict[Operation, str] = {
            Operation.READ: "read",
            Operation.WRITE: "write",
            Operation.SEARCH: "read",
            Operation.EXECUTE: "write",
            Operation.DELETE: "write",
        }

    def _is_sensitive_path(self, path: Path) -> bool:
        """检查路径是否匹配敏感文件模式."""
        import re

        try:
            rel_str = str(path.relative_to(self._root)).replace("\\", "/")
        except ValueError:
            return True  # 工作区外的路径视为敏感

        return any(re.search(pattern, rel_str) for pattern in self._sensitive_patterns)

    def check(self, tool_name: str, path: Path, operation: Operation) -> Decision:
        """检查工具能否对路径执行操作.

        决策流程:
        1. 如果路径在工作区外 → DENIED
        2. 如果是敏感文件且操作非 SEARCH → DENIED
        3. 如果是二进制文件且操作是 READ/WRITE → 特殊处理(记录而非禁止)
        4. 否则 → ALLOWED

        Args:
            tool_name: 工具名称(如 "read_tool", "write_tool")
            path: 目标路径
            operation: 操作类型

        Returns:
            权限决策结果
        """
        # 1. 工作区边界(双重保障, PathValidator 已做)
        try:
            path.relative_to(self._root)
        except ValueError:
            return Decision.DENIED

        # 2. 敏感文件保护(禁止 READ/WRITE/EXECUTE/DELETE)
        if operation in (
            Operation.READ,
            Operation.WRITE,
            Operation.EXECUTE,
            Operation.DELETE,
        ) and self._is_sensitive_path(path):
            return Decision.DENIED

        # 3. 二进制文件: 允许但标记 (记录由调用方处理)
        # 这里不做禁止, 仅在 query 中返回信息

        return Decision.ALLOWED

    def is_allowed(self, tool_name: str, path: Path, operation: Operation) -> bool:
        """快捷方法: 是否允许操作."""
        return self.check(tool_name, path, operation) == Decision.ALLOWED
