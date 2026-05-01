"""二进制文件检测工具模块.

提供统一的二进制文件判断逻辑:
1. 常见二进制后缀名直接判定为二进制文件
2. 否则尝试以指定编码解码前 512 字节,解码失败则认为是二进制文件或编码错误
"""

from pathlib import Path

# 常见二进制文件扩展名(小写)
BINARY_EXTENSIONS: frozenset[str] = frozenset(
    {
        # 可执行文件
        ".exe",
        ".dll",
        ".so",
        ".dylib",
        ".bin",
        ".com",
        ".msi",
        ".bat",
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
        ".svg",
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
        # 文档/电子书
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
        # 其他
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
        ".env",
    }
)

# 解码检测时读取的最大字节数
_DETECTION_CHUNK_SIZE = 512


def is_binary_file(path: str | Path, encoding: str = "utf-8") -> bool:
    """判断给定路径是否为二进制文件.

    判定策略:
    1. 如果文件不存在,仅通过扩展名判断(适用于写入前的预检查)
    2. 如果扩展名在已知二进制列表中,直接返回 True
    3. 否则读取文件前 512 字节,尝试以指定编码解码;解码失败则认为是二进制文件

    Args:
        path: 文件路径
        encoding: 尝试解码时使用的编码,默认 "utf-8"

    Returns:
        True 表示是二进制文件, False 表示可能是文本文件
    """
    p = Path(path)
    suffix = p.suffix.lower()

    # 策略1: 扩展名匹配
    if suffix in BINARY_EXTENSIONS:
        return True

    # 策略2: 文件不存在时,无法通过内容判断,返回 False(允许创建)
    if not p.exists():
        return False

    # 策略3: 尝试以指定编码解码文件头部
    try:
        with open(p, "rb") as f:
            chunk = f.read(_DETECTION_CHUNK_SIZE)
        if not chunk:
            # 空文件视为文本文件
            return False
        # 即使解码成功,null 字节也几乎不可能出现在合法文本文件中
        if b"\x00" in chunk:
            return True
        chunk.decode(encoding)
        return False
    except UnicodeDecodeError, ValueError:
        return True
    except OSError:
        # 文件无法读取(权限等),保守返回 False
        return False
