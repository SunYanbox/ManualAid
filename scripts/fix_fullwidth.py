#!/usr/bin/env python3
"""检测并修复项目中的全角字符问题。

用法:
    python scripts/fix_fullwidth.py check [--exclude PATH...]
    python scripts/fix_fullwidth.py write [--exclude PATH...]
"""

import re
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text

# 全角到半角映射表
FULLWIDTH_MAP = {
    "，": ",",
    "。": ".",
    "（": "(",
    "）": ")",
    "；": ";",
    "：": ":",
    "！": "!",
    "？": "?",
    "“": '"',
    "”": '"',
    "‘": "'",
    "’": "'",
    "【": "[",
    "】": "]",
    "《": "<",
    "》": ">",
    "～": "~",
    "＠": "@",
    "＃": "#",
    "＄": "$",
    "％": "%",
    "＾": "^",
    "＆": "&",
    "＊": "*",
    "＿": "_",
    "＋": "+",
    "＝": "=",
    "｜": "|",
    "＼": "\\",
    "／": "/",
}

# 需要扫描的文件扩展名
TARGET_EXTS = {".py", ".md"}

# 默认排除路径
DEFAULT_EXCLUDE = {
    ".venv",
    "venv",
    "__pycache__",
    ".git",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "build",
    "dist",
    "node_modules",
}

console = Console()


class FullwidthChecker:
    def __init__(
        self,
        root_path: str = ".",
        exclude_patterns: list[str] | None = None,
        page_size: int = 15,
    ):
        self.root = Path(root_path).resolve()
        self.pattern = re.compile("|".join(re.escape(k) for k in FULLWIDTH_MAP))
        self.issues = []
        self.page_size = page_size

        # 构建排除列表
        self.exclude_patterns = set(DEFAULT_EXCLUDE)
        if exclude_patterns:
            self.exclude_patterns.update(exclude_patterns)

        self.exclude_dirs = []  # 排除的目录
        self.exclude_files = []  # 排除的文件

        for pattern in self.exclude_patterns:
            full_path = self.root / pattern
            if full_path.exists():
                if full_path.is_dir():
                    self.exclude_dirs.append(pattern)
                elif full_path.is_file():
                    self.exclude_files.append(pattern)
            else:
                # 路径不存在时, 根据是否有扩展名猜测
                if "." in Path(pattern).name:
                    self.exclude_files.append(pattern)
                else:
                    self.exclude_dirs.append(pattern)

        # 确保脚本自身被排除
        script_file = Path(__file__)
        try:
            rel_script = script_file.relative_to(self.root)
            self.exclude_patterns.add(str(rel_script))
        except ValueError:
            # 脚本不在项目根目录下, 忽略
            pass

    def _should_exclude(self, path: Path) -> bool:
        """检查路径是否应被排除。"""
        try:
            rel_path = path.relative_to(self.root)
        except ValueError:
            return False

        parts = rel_path.parts
        for exclude in self.exclude_patterns:
            exclude_path = Path(exclude)
            if len(exclude_path.parts) == 1:
                # 简单名称匹配(如 ".venv")
                if exclude in parts:
                    return True
            else:
                # 路径匹配
                try:
                    rel_path.relative_to(exclude)
                    return True
                except ValueError:
                    pass
        return False

    def _display_exclude_info(self) -> None:
        """显示配置的排除路径信息。"""
        if not self.exclude_dirs and not self.exclude_files:
            return

        console.print()
        console.print("[dim]🚫 排除配置:[/dim]")

        if self.exclude_dirs:
            dirs_str = ", ".join(sorted(self.exclude_dirs))
            console.print(f"   [dim]📁 目录: {dirs_str}[/dim]")

        if self.exclude_files:
            files_str = ", ".join(sorted(self.exclude_files))
            console.print(f"   [dim]📄 文件: {files_str}[/dim]")

    def scan(self, show_progress: bool = True) -> bool:
        """扫描所有目标文件,返回是否有问题。"""
        self.issues = []

        # 收集所有目标文件
        console.print("[dim]📂 正在收集文件...[/dim]")
        all_files = []
        for ext in TARGET_EXTS:
            all_files.extend(self.root.rglob(f"*{ext}"))

        # 过滤排除的路径
        files = []
        excluded_count = 0
        for f in all_files:
            if self._should_exclude(f):
                excluded_count += 1
                continue
            files.append(f)

        if excluded_count > 0:
            console.print(f"[dim]🚫 已排除 {excluded_count} 个文件/目录[/dim]")

        if not files:
            console.print("[yellow]⚠ 未找到需要扫描的 .py 或 .md 文件[/yellow]")
            return True

        console.print(f"[dim]📄 找到 {len(files)} 个文件待扫描[/dim]")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            if show_progress:
                task = progress.add_task("[cyan]🔍 扫描全角字符...", total=len(files))

            for file_path in files:
                self._check_file(file_path)
                if show_progress:
                    progress.advance(task)

        return len(self.issues) == 0

    def _check_file(self, file_path: Path) -> None:
        """检测单个文件中的全角字符。"""
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            console.print(f"[red]✗ 无法读取 {file_path}: {e}[/red]")
            return

        lines = content.splitlines(keepends=False)
        for line_num, line in enumerate(lines, 1):
            matches = list(self.pattern.finditer(line))
            for match in matches:
                char = match.group(0)
                self.issues.append(
                    {
                        "file": str(file_path),
                        "line": line_num,
                        "char": char,
                        "replacement": FULLWIDTH_MAP[char],
                        "context": line.strip()[:60],
                    }
                )

    def _display_page(self, issues: list[dict], start_idx: int, total: int) -> bool:
        """显示一页问题列表,返回是否继续。"""
        console.clear()

        # 显示进度
        end_idx = min(start_idx + self.page_size, total)
        console.print(f"\n[bold cyan]问题 {start_idx + 1}-{end_idx} / {total}[/bold cyan]")
        console.print("─" * console.width)

        # 创建表格
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("#", style="dim", width=4)
        table.add_column("文件", style="cyan", width=35)
        table.add_column("行", style="dim", width=5)
        table.add_column("全角", style="red", width=5)
        table.add_column("→", style="dim", width=2)
        table.add_column("半角", style="green", width=5)
        table.add_column("上下文", style="yellow", width=40)

        for i, issue in enumerate(issues[start_idx:end_idx], start=start_idx + 1):
            file_path = Path(issue["file"])
            try:
                rel_path = file_path.relative_to(self.root)
            except ValueError:
                rel_path = file_path

            # 截断过长路径
            rel_path_str = str(rel_path)
            if len(rel_path_str) > 32:
                rel_path_str = "..." + rel_path_str[-29:]

            table.add_row(
                str(i),
                rel_path_str,
                str(issue["line"]),
                f"'{issue['char']}'",
                "→",
                f"'{issue['replacement']}'",
                issue["context"] + ("..." if len(issue["context"]) == 60 else ""),
            )

        console.print(table)
        console.print()

        # 如果是最后一页
        if end_idx >= total:
            return False

        # 提示操作
        console.print("[dim]操作: [N]下一页  [P]上一页  [Q]退出  [Enter]继续[/dim]")

        while True:
            key = Prompt.ask("", default="n", show_default=False).lower()
            if key in ("", "n", "next"):
                return True
            elif key in ("p", "prev", "previous"):
                return "prev"
            elif key in ("q", "quit", "exit"):
                return False
            else:
                console.print("[yellow]无效输入,请重试[/yellow]")

    def report(self) -> None:
        """使用 Rich 美化打印检测结果(支持分页)。"""
        if not self.issues:
            panel = Panel(
                "[bold green]✅ 未发现全角字符问题![/bold green]",
                border_style="green",
            )
            console.print(panel)
            return

        # 统计信息
        files_count = len(set(i["file"] for i in self.issues))
        console.print()

        summary = Text()
        summary.append("⚠️  发现 ", style="bold yellow")
        summary.append(f"{len(self.issues)} ", style="bold red")
        summary.append("处全角字符问题,涉及 ", style="bold yellow")
        summary.append(f"{files_count} ", style="bold red")
        summary.append("个文件", style="bold yellow")
        console.print(Panel(summary, border_style="yellow"))

        # 按文件分组统计
        from collections import Counter

        file_counter = Counter(Path(i["file"]).name for i in self.issues)
        console.print("\n[bold]📊 问题分布:[/bold]")
        for filename, count in file_counter.most_common(5):
            console.print(f"  • {filename}: [yellow]{count}[/yellow] 处")
        console.print()

        # 分页显示详细问题
        console.print("[bold cyan]📋 详细问题列表(分页显示):[/bold cyan]")
        console.print("[dim]按 Enter 继续,输入 q 退出[/dim]\n")

        current_idx = 0
        while current_idx < len(self.issues):
            result = self._display_page(self.issues, current_idx, len(self.issues))

            if result is False:  # 用户退出
                console.print("[yellow]已退出查看[/yellow]")
                break
            elif result == "prev":
                current_idx = max(0, current_idx - self.page_size)
            else:  # True 或 "next"
                current_idx += self.page_size

        console.print()
        console.print("[bold cyan]💡 提示:[/bold cyan] 运行 [green]check_fullwidth.cmd write[/green] 自动修复")

    def fix(self) -> int:
        """修复所有检测到的问题。"""
        # 先扫描
        console.print("[cyan]🔍 正在扫描全角字符...[/cyan]")
        self.scan(show_progress=True)

        if not self.issues:
            console.print("[bold green]✅ 没有需要修复的问题。[/bold green]")
            return 0

        # 按文件分组
        files_dict = {}
        for issue in self.issues:
            files_dict.setdefault(issue["file"], []).append(issue)

        console.print(f"\n[bold yellow]🔧 准备修复 {len(files_dict)} 个文件...[/bold yellow]\n")

        fixed_count = 0
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("[cyan]修复中...", total=len(files_dict))

            for file_path_str, issues in files_dict.items():
                file_path = Path(file_path_str)
                try:
                    rel_path = file_path.relative_to(self.root)
                except ValueError:
                    rel_path = file_path

                try:
                    content = file_path.read_text(encoding="utf-8")
                    new_content = self.pattern.sub(lambda m: FULLWIDTH_MAP[m.group(0)], content)
                    file_path.write_text(new_content, encoding="utf-8")

                    count = len(issues)
                    fixed_count += count
                    console.print(f"  [green]✓[/green] {rel_path} [dim](修复 {count} 处)[/dim]")
                except Exception as e:
                    console.print(f"  [red]✗[/red] {rel_path}: {e}")
                    return 1
                finally:
                    progress.advance(task)

        console.print()
        panel = Panel(
            f"[bold green]✅ 修复完成!共修复 {fixed_count} 处全角字符问题。[/bold green]",
            border_style="green",
        )
        console.print(panel)
        return 0


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """🛠️  检测并修复项目中的全角字符问题。

    支持的文件类型:.py、.md

    \b
    示例:
      check_fullwidth.cmd check
      check_fullwidth.cmd check --exclude tests docs/examples
      check_fullwidth.cmd write --exclude legacy/
    """
    if ctx.invoked_subcommand is None:
        console.print("[yellow]请指定子命令: check 或 write[/yellow]")
        console.print(ctx.get_help())
        sys.exit(1)


@cli.command()
@click.option(
    "--exclude",
    "-e",
    multiple=True,
    help="排除的目录或文件(可多次使用)。例如: --exclude tests --exclude docs/old",
)
@click.option("--page-size", "-p", default=15, help="分页显示时每页显示的问题数量(默认: 15)")
def check(exclude: list[str], page_size: int):
    """🔍 仅检测全角字符问题(不修改文件)"""
    checker = FullwidthChecker(exclude_patterns=list(exclude) if exclude else None, page_size=page_size)

    console.print(Panel.fit("[bold blue]🔍 全角字符检测模式[/bold blue]", border_style="blue"))

    if exclude:
        console.print(f"[dim]🚫 排除路径: {', '.join(exclude)}[/dim]")

    checker._display_exclude_info()

    is_clean = checker.scan()
    checker.report()
    sys.exit(0 if is_clean else 1)


@cli.command()
@click.option(
    "--exclude",
    "-e",
    multiple=True,
    help="排除的目录或文件(可多次使用)。例如: --exclude tests --exclude docs/old",
)
def write(exclude: list[str]):
    """✏️  检测并自动修复全角字符问题"""
    checker = FullwidthChecker(exclude_patterns=list(exclude) if exclude else None)

    console.print(Panel.fit("[bold yellow]✏️  全角字符修复模式[/bold yellow]", border_style="yellow"))

    if exclude:
        console.print(f"[dim]🚫 排除路径: {', '.join(exclude)}[/dim]")

    checker._display_exclude_info()

    sys.exit(checker.fix())


if __name__ == "__main__":
    cli()
