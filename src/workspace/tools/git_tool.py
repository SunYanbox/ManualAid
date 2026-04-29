"""统一的 Git 工具 — 白名单机制,安全封装."""

import re
import shlex
import subprocess

from src.models.tool_error_response import ToolErrorResponse
from src.workspace.tools.base_tool import BaseTool
from src.workspace.workspace import Workspace

# 安全命令(只读,直接执行,不需要审核)
_SAFE_COMMANDS = frozenset({"status", "diff", "log", "show"})

# 白名单(所有允许的命令)
_ALLOWED_COMMANDS = frozenset(
    {
        "status",
        "diff",
        "log",
        "add",
        "commit",
        "restore",
        "show",
        "branch",
    }
)

# 拦截正则 — 即使白名单允许的也再检查一次
_BLOCKED_PATTERNS = [
    re.compile(r"\bpush\b"),
    re.compile(r"\bremote\b"),
    re.compile(r"\breset\s+--hard\b"),
    re.compile(r"\bbranch\s+-D\b"),
    re.compile(r"\bmerge\b"),
    re.compile(r"\brebase\b"),
    re.compile(r"\bclean\b"),
    re.compile(r"\bcheckout\s+-B\b"),
    re.compile(r"\bcherry-pick\b"),
    re.compile(r"\btag\b"),
    re.compile(r"\bfetch\b"),
    re.compile(r"\bpull\b"),
]


class GitTool(BaseTool):
    """统一的 Git 工具 — 安全的子命令执行.

    白名单机制:
    - 安全命令 (status, diff, log, show): 直接执行,不触发审核
    - 修改命令 (add, commit, restore, branch): 执行并标记 PENDING_AUDIT
    - 禁止命令 (push, reset --hard, merge, rebase, ...): 拦截并返回错误
    """

    def __init__(self, workspace: Workspace):
        super().__init__(workspace, "git", self.git.__doc__, read_permission=True)
        self.func = self.git
        self.params = BaseTool.extract_params(self.git)

    def git(self, command_str: str) -> str:
        """
        执行 Git 命令(白名单限制)

        Parameters
        ----------
        command_str: Git 子命令及其参数,如 "status"、"diff --cached"、"log --oneline -5"
        """
        if not command_str or not command_str.strip():
            return ToolErrorResponse(self.__class__.__name__, ValueError("command_str 不能为空")).to_str()

        try:
            tokens = shlex.split(command_str)
        except ValueError as e:
            return ToolErrorResponse(self.__class__.__name__, e).to_str()

        if not tokens:
            return ToolErrorResponse(self.__class__.__name__, ValueError("无法解析命令")).to_str()

        base_command = tokens[0]

        # 1. 白名单检查
        if base_command not in _ALLOWED_COMMANDS:
            allowed_list = ", ".join(sorted(_ALLOWED_COMMANDS))
            return (
                f"ERROR: Git command '{base_command}' is not in the allowed whitelist.\n"
                f"Allowed commands: {allowed_list}"
            )

        # 2. 拦截正则检查
        for pattern in _BLOCKED_PATTERNS:
            if pattern.search(command_str):
                return (
                    f"ERROR: The command was blocked by security policy.\n"
                    f"Pattern matched: {pattern.pattern}\n"
                    f"Command: {command_str}"
                )

        # 3. restore 安全检查 — 必须指定文件路径
        if base_command == "restore":
            non_flag_args = [t for t in tokens[1:] if not t.startswith("-")]
            if not non_flag_args:
                return ToolErrorResponse(
                    self.__class__.__name__,
                    ValueError("restore 需要指定文件路径,不允许裸 restore"),
                ).to_str()
            for arg in non_flag_args:
                stripped = arg.strip()
                if stripped in (".", "*", "all") or stripped.startswith("*"):
                    return ToolErrorResponse(
                        self.__class__.__name__,
                        ValueError("restore 需要指定具体文件路径,不允许使用通配符"),
                    ).to_str()

        # 4. 执行命令
        try:
            result = subprocess.run(
                ["git", *tokens],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(self.workspace.root_path),
            )
        except FileNotFoundError:
            return ToolErrorResponse(
                self.__class__.__name__,
                OSError("Git 未安装或不在系统 PATH 中"),
            ).to_str()
        except subprocess.TimeoutExpired:
            return ToolErrorResponse(
                self.__class__.__name__,
                TimeoutError("Git 命令执行超时(30 秒)"),
            ).to_str()

        # 5. 处理输出
        if result.returncode != 0:
            stderr = result.stderr.strip()
            if stderr:
                return f"Git command failed (exit code {result.returncode}):\n{stderr}"
            return f"Git command failed (exit code {result.returncode})"

        # Combine stdout and stderr
        output_parts = []
        if result.stdout:
            output_parts.append(result.stdout.rstrip("\n"))
        if result.stderr:
            output_parts.append(result.stderr.rstrip("\n"))

        return "\n".join(output_parts) if output_parts else "(no output)"

    @staticmethod
    def is_safe_command(command_str: str) -> bool:
        """判断一个 git 命令是否安全(只读,不需要审核).

        Args:
            command_str: 完整的 git 命令字符串

        Returns:
            如果是安全命令返回 True,否则返回 False
        """
        if not command_str or not command_str.strip():
            return False
        try:
            tokens = shlex.split(command_str)
        except ValueError:
            return False
        if not tokens:
            return False
        return tokens[0] in _SAFE_COMMANDS
