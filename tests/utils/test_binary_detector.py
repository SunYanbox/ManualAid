"""二进制文件检测工具的单元测试."""

from pathlib import Path

import pytest

from src.utils.binary_detector import BINARY_EXTENSIONS, is_binary_file


class TestBinaryExtensionDetection:
    """测试基于扩展名的二进制文件检测."""

    @pytest.mark.parametrize(
        "ext",
        [
            ".exe",
            ".dll",
            ".so",
            ".bin",
            ".zip",
            ".png",
            ".jpg",
            ".mp3",
            ".mp4",
            ".pdf",
            ".doc",
            ".pyc",
            ".whl",
            ".woff",
            ".sqlite",
            ".env",
            ".gz",
            ".7z",
            ".webp",
            ".svg",
            ".ttf",
        ],
    )
    def test_known_binary_extensions(self, tmp_path: Path, ext: str):
        """已知二进制扩展名应被检测为二进制文件."""
        f = tmp_path / f"test{ext}"
        f.write_bytes(b"\x00")
        assert is_binary_file(f) is True

    @pytest.mark.parametrize(
        "ext",
        [
            ".txt",
            ".py",
            ".js",
            ".ts",
            ".md",
            ".json",
            ".yaml",
            ".yml",
            ".toml",
            ".cfg",
            ".ini",
            ".csv",
            ".xml",
            ".html",
            ".css",
            ".sh",
            ".bash",
            ".zsh",
            ".c",
            ".h",
            ".cpp",
            ".hpp",
            ".rs",
            ".go",
            ".java",
            ".kt",
            ".rb",
            ".php",
            ".sql",
            ".log",
        ],
    )
    def test_known_text_extensions(self, tmp_path: Path, ext: str):
        """已知文本扩展名应不被检测为二进制文件."""
        f = tmp_path / f"test{ext}"
        f.write_text("hello world", encoding="utf-8")
        assert is_binary_file(f) is False

    def test_extension_case_insensitive(self, tmp_path: Path):
        """扩展名检测应不区分大小写."""
        f = tmp_path / "test.PNG"
        f.write_bytes(b"\x00")
        assert is_binary_file(f) is True

    def test_extension_without_dot(self, tmp_path: Path):
        """无扩展名的文件不应被扩展名规则匹配."""
        f = tmp_path / "Makefile"
        f.write_text("all:", encoding="utf-8")
        assert is_binary_file(f) is False


class TestBinaryContentDetection:
    """测试基于文件内容的二进制文件检测."""

    def test_null_bytes_in_content(self, tmp_path: Path):
        """包含 null 字节的内容应被检测为二进制."""
        f = tmp_path / "data.dat"
        f.write_bytes(b"hello\x00world")
        assert is_binary_file(f) is True

    def test_invalid_utf8_sequence(self, tmp_path: Path):
        """无效 UTF-8 字节序列应被检测为二进制."""
        f = tmp_path / "data.unknown"
        f.write_bytes(b"\xff\xfe\xfd\xfc")
        assert is_binary_file(f) is True

    def test_valid_utf8_content(self, tmp_path: Path):
        """有效的 UTF-8 文本内容不应被检测为二进制."""
        f = tmp_path / "data.unknown"
        f.write_text("这是一段中文文本\nwith english", encoding="utf-8")
        assert is_binary_file(f) is False

    def test_empty_file(self, tmp_path: Path):
        """空文件不应被检测为二进制."""
        f = tmp_path / "empty.unknown"
        f.write_bytes(b"")
        assert is_binary_file(f) is False

    def test_small_file(self, tmp_path: Path):
        """小于 512 字节的文件也能正确检测."""
        f = tmp_path / "small.unknown"
        f.write_bytes(b"\x01\x02\x03\xff")
        assert is_binary_file(f) is True

    def test_large_file_only_reads_header(self, tmp_path: Path):
        """大文件只检测前 512 字节."""
        f = tmp_path / "large.unknown"
        # 前 512 字节是有效 UTF-8,后面是二进制
        header = "x" * 512
        binary_tail = b"\xff" * 1024
        f.write_bytes(header.encode("utf-8") + binary_tail)
        assert is_binary_file(f) is False


class TestEncodingParameter:
    """测试 encoding 参数对检测的影响."""

    def test_gb18030_encoded_file_with_utf8_detection(self, tmp_path: Path):
        """GB18030 编码的中文文件在 UTF-8 检测下应被判为二进制."""
        f = tmp_path / "chinese.txt"
        # GB18030 编码的 "中文"
        f.write_bytes(b"\xd6\xd0\xce\xc4")
        assert is_binary_file(f, encoding="utf-8") is True

    def test_gb18030_encoded_file_with_gb18030_detection(self, tmp_path: Path):
        """GB18030 编码的文件在 GB18030 检测下应不被判为二进制."""
        f = tmp_path / "chinese.txt"
        f.write_bytes(b"\xd6\xd0\xce\xc4")
        assert is_binary_file(f, encoding="gb18030") is False


class TestNonExistentFile:
    """测试文件不存在时的行为."""

    def test_nonexistent_with_binary_ext(self, tmp_path: Path):
        """不存在的文件如果扩展名为二进制,仍应返回 True."""
        f = tmp_path / "new.exe"
        assert is_binary_file(f) is True

    def test_nonexistent_with_text_ext(self, tmp_path: Path):
        """不存在的文件如果扩展名为文本,应返回 False(允许创建)."""
        f = tmp_path / "new.txt"
        assert is_binary_file(f) is False

    def test_nonexistent_without_ext(self, tmp_path: Path):
        """不存在的文件如果无扩展名,应返回 False."""
        f = tmp_path / "newfile"
        assert is_binary_file(f) is False


class TestBinaryExtensionsSet:
    """测试 BINARY_EXTENSIONS 常量的完整性."""

    def test_is_frozenset(self):
        """BINARY_EXTENSIONS 应为 frozenset,防止意外修改."""
        assert isinstance(BINARY_EXTENSIONS, frozenset)

    def test_all_lower_case(self):
        """所有扩展名应为小写."""
        for ext in BINARY_EXTENSIONS:
            assert ext == ext.lower(), f"扩展名 {ext} 不是小写"

    def test_all_start_with_dot(self):
        """所有扩展名应以点号开头."""
        for ext in BINARY_EXTENSIONS:
            assert ext.startswith("."), f"扩展名 {ext} 不以点号开头"
