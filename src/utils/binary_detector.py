"""二进制文件检测工具模块.

基于文件后缀名和 MIME 类型判断文件是否为二进制文件
不读取文件内容,避免误判和性能问题
"""

import mimetypes
from pathlib import Path

# 初始化 mimetypes
mimetypes.init()

# 明确的文本文件扩展名
_TEXT_EXTENSIONS: frozenset[str] = frozenset(
    {
        # 源代码
        ".py",
        ".js",
        ".ts",
        ".jsx",
        ".tsx",
        ".go",
        ".rs",
        ".java",
        ".c",
        ".cpp",
        ".h",
        ".hpp",
        ".cs",
        ".rb",
        ".php",
        ".swift",
        ".kt",
        ".scala",
        ".lua",
        ".pl",
        ".pm",
        ".r",
        ".sql",
        # 配置文件
        ".json",
        ".jsonc",
        ".jsonl",
        ".yaml",
        ".yml",
        ".toml",
        ".ini",
        ".cfg",
        ".conf",
        ".xml",
        ".properties",
        ".env",
        ".env.example",
        ".gitignore",
        ".dockerignore",
        # 脚本
        ".sh",
        ".bash",
        ".zsh",
        ".fish",
        ".ps1",
        ".cmd",
        # 文档标记语言
        ".md",
        ".markdown",
        ".rst",
        ".txt",
        ".log",
        ".csv",
        ".tsv",
        ".tex",
        # Web 相关
        ".html",
        ".htm",
        ".css",
        ".scss",
        ".sass",
        ".less",
        ".vue",
        ".svelte",
        # 其他文本格式
        ".bat",  # Windows 批处理
        ".vbs",  # VBScript
        ".reg",  # Windows Registry
        ".desktop",
        # Godot
        ".godot",
        ".gd",
        ".gd.uid",
        ".tscn",
    }
)

# 明确的二进制文件扩展名
_BINARY_EXTENSIONS: frozenset[str] = frozenset(
    {
        # 可执行文件
        ".exe",
        ".dll",
        ".so",
        ".dylib",
        ".bin",
        ".com",
        ".msi",
        # 压缩文件
        ".zip",
        ".tar",
        ".gz",
        ".bz2",
        ".xz",
        ".7z",
        ".rar",
        ".zst",
        ".tgz",
        ".tbz2",
        ".txz",
        # 图片文件
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".bmp",
        ".ico",
        ".webp",
        ".tiff",
        ".tif",
        ".psd",
        ".raw",
        ".heic",
        ".avif",
        # 音视频文件
        ".mp3",
        ".mp4",
        ".avi",
        ".mkv",
        ".mov",
        ".wmv",
        ".flv",
        ".wav",
        ".ogg",
        ".flac",
        ".aac",
        ".m4a",
        ".m4v",
        ".webm",
        # 文档
        ".pdf",
        ".doc",
        ".docx",
        ".xls",
        ".xlsx",
        ".ppt",
        ".pptx",
        ".odt",
        ".ods",
        ".odp",
        ".epub",
        ".mobi",
        ".rtf",
        # 数据/序列化
        ".pickle",
        ".pkl",
        ".parquet",
        ".arrow",
        ".feather",
        ".h5",
        ".hdf5",
        # 其他二进制
        ".pyc",
        ".pyo",
        ".whl",
        ".egg",
        ".deb",
        ".rpm",
        ".dmg",
        ".iso",
        ".img",
        ".vhd",
        ".ova",
        ".apk",
        ".aab",
        ".ipa",
        ".woff",
        ".woff2",
        ".ttf",
        ".otf",
        ".eot",
        ".db",
        ".sqlite",
        ".sqlite3",
    }
)


def is_binary_file(path: str | Path) -> bool:
    """判断给定路径是否为二进制文件(仅基于后缀名和 MIME 类型,不读取文件内容).

    判定策略:
    1. 如果文件扩展名在 _TEXT_EXTENSIONS 中 → 返回 False(文本文件)
    2. 如果文件扩展名在 _BINARY_EXTENSIONS 中 → 返回 True(二进制文件)
    3. 否则使用 mimetypes.guess_type() 判断 MIME 类型:
       - 如果 MIME 类型以 text/ 开头 → 返回 False
       - 如果 MIME 类型是 application/json、application/xml 等文本格式 → 返回 False
       - 其他情况(image/、video/、audio/、application/zip 等)→ 返回 True
    4. 无法判断时,默认返回 False(假定为文本文件)

    注意:此函数完全不读取文件内容,仅基于文件扩展名和 MIME 类型判断.
    这意味着如果文件扩展名与实际内容不符(如二进制文件使用 .txt 扩展名),
    可能会产生误判.但根据用户需求,这种边缘情况不予考虑.

    Args:
        path: 文件路径

    Returns:
        True 表示是二进制文件,False 表示是文本文件
    """
    p = Path(path)
    suffix = p.suffix.lower()

    # 策略1: 明确的文本扩展名
    if suffix in _TEXT_EXTENSIONS:
        return False

    # 策略2: 明确的二进制扩展名
    if suffix in _BINARY_EXTENSIONS:
        return True

    # 策略3: 使用 mimetypes 兜底判断
    mime_type, _ = mimetypes.guess_type(str(p))
    if mime_type:
        # 文本类型 MIME
        if mime_type.startswith("text/"):
            return False
        # 文本格式 MIME 返回 False, 其他类型返回 True
        return mime_type not in ("application/json", "application/xml", "application/javascript", "application/x-yaml")

    # 策略4: 无法判断时,默认假定为文本文件
    return False
