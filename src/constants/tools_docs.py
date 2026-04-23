# BaseTool(self, workspace: Workspace, name: str, doc: str, read: bool = True, write: bool = False)

LS_TOOL_DOC = """列出指定目录下的文件和文件夹. 返回相对路径列表, 并标记[Folder]或[File]"""

READ_TOOL_DOC = """
读取文件全部内容, 若指定max_lines>0,则仅读取前max_lines行, 返回字符串
"""

Glob_TOOL_DOC = """
在工作区内按通配符模式匹配并列出所有路径,带[Folder]或[File]的类型标记. 失败时返回错误信息
"""

ReadLines_TOOL_DOC = """
读取文件的指定行范围(行号从1开始), 可指定上下文行数扩展返回的实际行数范围,返回带行号的格式化内容
"""

REGEX_SEARCH_TOOL_DOC = """
使用正则表达式搜索文件内容, 支持上下文显示、文件过滤和忽略路径, 返回匹配详情; 适合代码与文档探索
"""

EXACT_SEARCH_TOOL_DOC = """
精确搜索字符串(支持大小写敏感/全词匹配)
"""


Write_TOOL_DOC = """
向文件写入内容, 注意:此操作会[覆盖]原文件内容,用户没有要求的情况下禁止使用
"""

# 只读工具

LS_TOOL = ("ls", LS_TOOL_DOC, True, False)
READ_TOOL = ("read", READ_TOOL_DOC, True, False)
Glob_TOOL = ("glob", Glob_TOOL_DOC, True, False)
ReadLines_TOOL = ("read_lines", ReadLines_TOOL_DOC, True, False)
REGEX_SEARCH_TOOL = ("regex_search", REGEX_SEARCH_TOOL_DOC, True, False)
EXACT_SEARCH_TOOL = ("exact_search", EXACT_SEARCH_TOOL_DOC, True, False)

# 只写工具

Write_TOOL = ("write", Write_TOOL_DOC, False, True)
