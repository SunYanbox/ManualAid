from src.models.commands import Command


def generate_help_text(cmds: list[Command]) -> str:
    """生成帮助文本,返回 Rich markup 字符串"""
    lines: list[str] = [
        "[bold magenta]可用命令[/bold magenta]\n",
        "  [cyan]名称[/cyan]          [cyan]别名[/cyan]              [cyan]描述[/cyan]",
        "  " + chr(9472) * 70,
    ]
    for cmd in cmds:
        alias_str = " | ".join(f"[italic magenta]{a}[/italic magenta]" for a in cmd.aliases)
        lines.append(f"  [cyan]{cmd.name:<16}[/cyan] {alias_str:<24} [grey85]{cmd.description}[/grey85]")
    lines.append("")
    lines.append("[bold cyan]工具:[/bold cyan]")
    lines.append("[dim]使用 XML 标签调用工具,格式如下:[/dim]")
    lines.append(
        """[yellow bold]
<func_call name="工具名称">
    <param name="参数名称">参数值</param>
</func_call>
        [/yellow bold]
        """
    )
    return "\n".join(lines)
