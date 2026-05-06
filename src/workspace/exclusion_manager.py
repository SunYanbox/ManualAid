"""统一排除管理器 —— 合并 gitignore、用户 ignore、默认排除规则.

区分两类排除:
- 性能排除: 缓存/构建产物等不影响安全的目录
- 安全排除: 隐私/凭据文件等不应被 AI 访问的路径
"""

import os
import re
from pathlib import Path
from typing import ClassVar

from src.workspace.gitignore_loader import is_ignored_by_gitignore, load_gitignore


class ExclusionManager:
    """排除规则统一管理器.

    聚合三类排除源:
    1. 默认排除(内置的缓存/构建/IDE 目录)
    2. .gitignore 规则(如项目中有 .gitignore 文件)
    3. 用户临时 ignore 参数

    Args:
        workspace_root: 工作区根目录
    """

    # 性能排除 —— 缓存、构建产物、IDE 配置等
    PERFORMANCE_EXCLUSIONS: frozenset[str] = frozenset(
        {
            ".git",
            "__pycache__",
            "node_modules",
            ".venv",
            "venv",
            "dist",
            "build",
            ".idea",
            ".vscode",
            ".ruff_cache",
            ".pytest_cache",
            ".mypy_cache",
            ".hypothesis",
            "htmlcov",
            ".coverage",
            "*.pyc",
            "*.pyo",
            ".eggs",
            "*.egg-info",
            ".tox",
            ".nox",
            ".svn",
            ".hg",
            ".bzr",
            "target",  # Rust build
            ".next",  # Next.js build
            ".nuxt",  # Nuxt build
            ".output",  # Nuxt output
        }
    )

    # 安全排除 —— 敏感文件, AI 不应读取
    SECURITY_EXCLUSIONS: frozenset[str] = frozenset(
        {
            ".env",
            ".env.*",
            "*.pem",
            "credentials.*",
            "*.key",
            "*.cert",
            "id_rsa",
            "id_ed25519",
            "*.cred",
            "*.secret",
            "**/vault/**",
        }
    )

    # 安全排除 —— 需要精确匹配的特定文件
    SENSITIVE_FILE_PATTERNS: ClassVar[list[str]] = [
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

    def __init__(self, workspace_root: str | Path):
        self._workspace_root = Path(workspace_root).resolve()
        # 从 .gitignore 加载
        self._raw_gitignore_patterns: list[str] = []
        self._gitignore_exclude_res: list[re.Pattern] = []
        self._gitignore_negate_res: list[re.Pattern] = []

        self._reload_gitignore()

        # 编译敏感文件正则
        self._sensitive_file_res: list[re.Pattern] = []
        for pat in self.SENSITIVE_FILE_PATTERNS:
            try:
                self._sensitive_file_res.append(re.compile(pat))
            except re.error:
                continue

    def _reload_gitignore(self) -> None:
        """(重新)加载 .gitignore."""
        raw, exclude_res, negate_res = load_gitignore(self._workspace_root)
        self._raw_gitignore_patterns = raw
        self._gitignore_exclude_res = exclude_res
        self._gitignore_negate_res = negate_res

    def _check_performance_exclusion(self, rel_path_str: str) -> bool:
        """检查路径是否匹配性能排除规则(基于目录名)."""
        # 将路径拆分为各层, 检查每层是否在排除集合中
        parts = rel_path_str.replace(os.sep, "/").split("/")
        for part in parts:
            # 检查部分匹配: "node_modules" 或通配匹配
            if part in self.PERFORMANCE_EXCLUSIONS:
                return True
            # 检查 *.xxx 模式
            for exclude in self.PERFORMANCE_EXCLUSIONS:
                if exclude.startswith("*.") and part.endswith(exclude[1:]):
                    return True
        return False

    def should_exclude_dir(self, dir_name: str) -> bool:
        """检查目录名是否应该被排除(基于名称的快速检查).

        用于 glob/ls 等基于目录名的过滤场景.
        """
        return dir_name in self.PERFORMANCE_EXCLUSIONS

    def should_exclude_path(self, path: Path) -> bool:
        """检查路径是否应被排除(全面检查).

        依次检查: 默认排除目录名 → gitignore 规则 → 否定规则

        Args:
            path: 文件的绝对路径

        Returns:
            True 表示应排除
        """
        try:
            rel_path = path.relative_to(self._workspace_root)
        except ValueError:
            # 在工作区外, 不在这里处理(由 PathValidator 处理)
            return False

        rel_str = str(rel_path).replace(os.sep, "/")

        # 1. 性能排除: 检查所有父目录
        if self._check_performance_exclusion(rel_str):
            return True

        # 2. gitignore 排除
        return is_ignored_by_gitignore(rel_str, self._gitignore_exclude_res, self._gitignore_negate_res)

    def is_sensitive_file(self, path: Path) -> bool:
        """检查路径是否为敏感文件.

        Args:
            path: 文件绝对路径

        Returns:
            True 表示是敏感文件
        """
        try:
            rel_str = str(path.relative_to(self._workspace_root)).replace(os.sep, "/")
        except ValueError:
            return False

        return any(regex.search(rel_str) for regex in self._sensitive_file_res)

    def merge_ignore_regexes(self, user_ignore: list[str] | None = None) -> list[re.Pattern]:
        """合并默认排除 + gitignore + 用户 ignore 为正则列表.

        用于 search_content 等需要正则匹配排除的场景.

        Args:
            user_ignore: 用户传入的忽略正则列表

        Returns:
            编译后的正则列表
        """
        result: list[re.Pattern] = []

        # 默认排除目录名 → 正则
        for excl in self.PERFORMANCE_EXCLUSIONS:
            # 处理 *.pyc 类模式
            if excl.startswith("*."):
                pat = excl[1:]  # .pyc
                result.append(re.compile(re.escape(pat) + "$"))
            else:
                # 匹配路径中的此目录名
                result.append(re.compile(r"(^|/)" + re.escape(excl) + r"(/|$)"))

        # gitignore 排除正则
        result.extend(self._gitignore_exclude_res)

        # 用户传入的 ignore 正则
        if user_ignore:
            for ign in user_ignore:
                try:
                    result.append(re.compile(ign))
                except re.error:
                    continue

        return result

    @property
    def excluded_dir_names(self) -> set[str]:
        """获取所有排除目录名集合(用于快速 in 检查)."""
        return {d for d in self.PERFORMANCE_EXCLUSIONS if not d.startswith("*")}
