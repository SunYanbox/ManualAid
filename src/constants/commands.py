HELP_MESSAGE: str = """[bold]Available Commands:[/bold]
  /copy <n>  or /c <n>  - Copy result #n to clipboard (no <n> copies last)
  /history               - Show command history
  /help       or /h      - Show this help message
  /tools       or /t     - List available tools
  /tool <name>           - Show tool details
  /prompt   or /pmt      - Generate LLM tool call prompt
  /workspace   or /ws    - Generate workspace metadata prompt
  /view       or /v      - Open interactive result viewer
  /view_clear            - Clear all items from viewer
  /view_remove <n>       - Remove item #n from viewer
  /quit       or /q      - Exit console
  <func_call>...         - Execute tool call

[bold]Viewer Controls:[/bold]
  ↑/↓: Navigate items
  Enter/Space: Expand/Collapse
  Delete: Remove current item
  Home/End: Jump to first/last
  q/Esc: Exit viewer"""
