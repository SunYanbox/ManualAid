# BaseTool(self, workspace: Workspace, name: str, doc: str, read: bool = True, write: bool = False)

LS_TOOL_DOC = """列出工作区内指定目录下的文件和文件夹,带[Folder]/[File]标记.失败时返回错误字符串"""

READ_TOOL_DOC = """
读取工作区内指定文件的全部内容,返回字符串.失败时返回错误描述.
"""

Glob_TOOL_DOC = """
在工作区内按通配符模式匹配并列出所有路径,带类型标记.失败时返回错误字符串
"""

ReadLines_TOOL_DOC = """
读取工作区内文件的指定行范围(行号从1开始),返回带行号和文件头格式的内容.失败时返回错误信息
"""

REGEX_SEARCH_TOOL_DOC = """
使用正则表达式在工作区内搜索文件内容,支持显示匹配行的上下文、按文件模式过滤、忽略指定路径
"""

EXACT_SEARCH_TOOL_DOC = """
在工作区内精确搜索字符串(大小写敏感、全词匹配),专用于安全审计场景,支持忽略指定路径
"""


Write_TOOL_DOC = """
在工作区文件中***覆盖原文件**的写入新的内容
"""

# 只读工具

LS_TOOL = ("ls", LS_TOOL_DOC, True, False)
READ_TOOL = ("read", READ_TOOL_DOC, True, False)
Glob_TOOL = ("glob", Glob_TOOL_DOC, True, False)
ReadLines_TOOL = ("read_lines", READ_TOOL_DOC, True, False)
REGEX_SEARCH_TOOL = ("regex_search", REGEX_SEARCH_TOOL_DOC, True, False)
EXACT_SEARCH_TOOL = ("exact_search", EXACT_SEARCH_TOOL_DOC, True, False)

# 只写工具

Write_TOOL = ("write", Write_TOOL_DOC, False, True)
