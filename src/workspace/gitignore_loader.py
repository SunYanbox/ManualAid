"""Parse .gitignore files and convert patterns to regex for exclusion matching.

已知局限性:
- 不支持嵌套 .gitignore(仅读取根目录下的 .gitignore)
- 不支持行尾 \\ 续行
- 不支持 gitignore 扩展语法中的字符类(如 [abc] 会被错误转义)
- 否定模式的优先级处理与真实 Git 不一致: 当前实现将所有否定模式提升为最高优先级,
  而真实 Git 按行号顺序逐条处理(后出现的规则覆盖先出现的).
  当前行为对于 AI 工具场景偏安全(宁可少排除), 故保留此简化实现.
"""

from __future__ import annotations

import os
import re
from pathlib import Path


def _convert_gitignore_to_regex(pattern: str) -> str | None:
    """将 .gitignore 模式转换为正则表达式.

    Args:
        pattern: .gitignore 模式(如 *.log, build/, /foo)

    Returns:
        对应的正则表达式字符串, 如果模式无效则返回 None
    """
    # 保留原始模式用于锚定判断
    original = pattern
    is_dir_only = pattern.endswith("/")
    if is_dir_only:
        pattern = pattern.rstrip("/")

    # 处理否定模式(仅用于判断是否为目录模式, 不处理逻辑)
    if pattern.startswith("!"):
        pattern = pattern[1:]

    # 转义正则特殊字符, 再处理 gitignore 通配符
    # 先处理 ** (多级通配符)
    parts = []
    i = 0
    while i < len(pattern):
        if pattern[i : i + 2] == "**":
            parts.append(".*")
            i += 2
        elif pattern[i] == "*":
            # 单级通配符, 不匹配路径分隔符
            parts.append(r"[^/]*")
            i += 1
        elif pattern[i] == "?":
            parts.append(r"[^/]")
            i += 1
        elif pattern[i] in ".+^${}()|[]\\":
            parts.append("\\" + pattern[i])
            i += 1
        else:
            parts.append(pattern[i])
            i += 1

    regex_str = "".join(parts)

    # 锚定: / 开头表示从根目录匹配, 否则匹配任意路径
    if original.startswith("/"):
        regex_str = "^" + regex_str[1:]  # 去掉开头的 /
    elif original.startswith("!"):
        # 处理否定模式 - 保持锚定逻辑不变
        regex_str = "^" + regex_str[1:] if original[1:].startswith("/") else "(^|/)" + regex_str
    else:
        regex_str = "(^|/)" + regex_str

    if is_dir_only:
        regex_str += "(/.*)?$"
    else:
        regex_str += "$"

    return regex_str


def parse_gitignore(gitignore_path: str | Path) -> list[str]:
    """解析 .gitignore 文件, 返回非否定排除模式列表.

    Args:
        gitignore_path: .gitignore 文件路径

    Returns:
        排除模式列表(目录名/通配符等原始 gitignore 格式)
    """
    patterns: list[str] = []
    gitignore_path = Path(gitignore_path)

    if not gitignore_path.exists():
        return patterns

    try:
        text = gitignore_path.read_text(encoding="utf-8")
    except Exception:
        return patterns

    for line in text.splitlines():
        stripped = line.strip()

        # 跳过空行和注释
        if not stripped or stripped.startswith("#"):
            continue

        # 保留否定模式供外部处理, 返回原始行
        patterns.append(stripped)

    return patterns


def compile_gitignore_patterns(patterns: list[str]) -> tuple[list[re.Pattern], list[re.Pattern]]:
    """将 gitignore 模式编译为正则表达式.

    Args:
        patterns: 原始 gitignore 模式列表

    Returns:
        (排除正则列表, 否定排除正则列表) 的元组
    """
    exclude_res: list[re.Pattern] = []
    negate_res: list[re.Pattern] = []

    for pattern in patterns:
        if pattern.startswith("!"):
            # 否定模式: 取消排除
            negate_regex = _convert_gitignore_to_regex(pattern)
            if negate_regex:
                try:
                    negate_res.append(re.compile(negate_regex))
                except re.error:
                    continue
        else:
            regex = _convert_gitignore_to_regex(pattern)
            if regex:
                try:
                    exclude_res.append(re.compile(regex))
                except re.error:
                    continue

    return exclude_res, negate_res


def is_ignored_by_gitignore(path: str | Path, exclude_res: list[re.Pattern], negate_res: list[re.Pattern]) -> bool:
    """检查路径是否被 .gitignore 规则忽略.

    Args:
        path: 要检查的相对路径(字符串形式)
        exclude_res: 排除正则列表
        negate_res: 否定排除正则列表

    Returns:
        是否应该被忽略
    """
    path_str = str(path).replace(os.sep, "/")

    # 先检查否定模式(优先级更高)
    for negate_re in negate_res:
        if negate_re.search(path_str):
            return False

    # 再检查排除模式
    return any(exclude_re.search(path_str) for exclude_re in exclude_res)


def load_gitignore(workspace_root: str | Path) -> tuple[list[str], list[re.Pattern], list[re.Pattern]]:
    """从工作区根目录加载 .gitignore.

    Args:
        workspace_root: 工作区根目录

    Returns:
        (原始模式列表, 排除正则列表, 否定排除正则列表)
    """
    gitignore_path = Path(workspace_root) / ".gitignore"
    raw_patterns = parse_gitignore(gitignore_path)
    exclude_res, negate_res = compile_gitignore_patterns(raw_patterns)
    return raw_patterns, exclude_res, negate_res
