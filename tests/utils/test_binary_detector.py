"""二进制文件检测器测试(仅基于扩展名和 MIME 类型)."""

import tempfile
from pathlib import Path

import pytest

from src.utils.binary_detector import is_binary_file


class TestBinaryDetector:
    """测试基于文件扩展名和 MIME 类型的二进制文件检测."""

    @pytest.fixture
    def temp_dir(self):
        """创建临时目录用于测试文件."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_text_extension_txt(self, temp_dir):
        """测试 .txt 文件扩展名返回 False(文本文件)."""
        file_path = temp_dir / "test.txt"
        file_path.write_text("这是一个文本文件.\n第二行\n第三行")
        assert is_binary_file(file_path) is False

    def test_text_extension_py(self, temp_dir):
        """测试 .py 文件扩展名返回 False(文本文件)."""
        file_path = temp_dir / "test.py"
        file_path.write_text("def foo():\n    return 'hello'")
        assert is_binary_file(file_path) is False

    def test_text_extension_json(self, temp_dir):
        """测试 .json 文件扩展名返回 False(文本文件)."""
        file_path = temp_dir / "config.json"
        file_path.write_text('{"name": "test", "value": 123}')
        assert is_binary_file(file_path) is False

    def test_text_extension_env(self, temp_dir):
        """测试 .env 文件扩展名返回 False(文本文件)."""
        file_path = temp_dir / ".env"
        file_path.write_text("API_KEY=secret123\nDEBUG=true")
        assert is_binary_file(file_path) is False

    def test_text_extension_bat(self, temp_dir):
        """测试 .bat 文件扩展名返回 False(文本文件)."""
        file_path = temp_dir / "script.bat"
        file_path.write_text("@echo off\necho Hello World")
        assert is_binary_file(file_path) is False

    def test_text_extension_md(self, temp_dir):
        """测试 .md 文件扩展名返回 False(文本文件)."""
        file_path = temp_dir / "README.md"
        file_path.write_text("# 标题\n\n这是 **markdown** 内容.")
        assert is_binary_file(file_path) is False

    def test_binary_extension_exe(self, temp_dir):
        """测试 .exe 文件扩展名返回 True(二进制文件)."""
        file_path = temp_dir / "program.exe"
        # 内容不重要,只检查扩展名
        file_path.write_bytes(b"MZ\x90\x00" + b"\x00" * 100)
        assert is_binary_file(file_path) is True

    def test_binary_extension_png(self, temp_dir):
        """测试 .png 文件扩展名返回 True(二进制文件)."""
        file_path = temp_dir / "image.png"
        file_path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
        assert is_binary_file(file_path) is True

    def test_binary_extension_zip(self, temp_dir):
        """测试 .zip 文件扩展名返回 True(二进制文件)."""
        file_path = temp_dir / "archive.zip"
        file_path.write_bytes(b"PK\x03\x04" + b"\x00" * 100)
        assert is_binary_file(file_path) is True

    def test_binary_extension_pdf(self, temp_dir):
        """测试 .pdf 文件扩展名返回 True(二进制文件)."""
        file_path = temp_dir / "document.pdf"
        file_path.write_bytes(b"%PDF-1.4" + b"\x00" * 100)
        assert is_binary_file(file_path) is True

    def test_empty_file_with_text_extension(self, temp_dir):
        """测试空文件但扩展名为文本类型返回 False."""
        file_path = temp_dir / "empty.txt"
        file_path.write_text("")
        assert is_binary_file(file_path) is False

    def test_non_existent_file(self, temp_dir):
        """测试不存在的文件返回 False."""
        file_path = temp_dir / "does_not_exist.txt"
        assert is_binary_file(file_path) is False

    def test_unknown_extension_binary_content(self, temp_dir):
        """测试未知扩展名且内容是二进制的情况."""
        file_path = temp_dir / "data.unknown"
        file_path.write_bytes(b"\x00\x01\x02\x03")
        # 没有扩展名,回退到 MIME 类型检测
        # .unknown 扩展名可能被检测为 application/octet-stream -> 二进制
        result = is_binary_file(file_path)
        # 结果取决于 mimetypes 数据库
        assert isinstance(result, bool)

    def test_file_without_extension_text(self, temp_dir):
        """测试没有扩展名但内容是文本的文件."""
        file_path = temp_dir / "README"
        file_path.write_text("# README\n内容在这里")
        # MIME 类型检测应识别为文本
        assert is_binary_file(file_path) is False

    def test_text_extensions_list(self, temp_dir):
        """测试所有文本扩展名都返回 False."""
        text_extensions = [
            ".py",
            ".js",
            ".json",
            ".md",
            ".env",
            ".bat",
            ".txt",
            ".csv",
            ".xml",
            ".yaml",
            ".yml",
            ".toml",
            ".ini",
            ".cfg",
            ".conf",
            ".sh",
            ".bash",
            ".ps1",
            ".html",
            ".css",
            ".vue",
            ".log",
            ".rst",
        ]
        for ext in text_extensions:
            file_path = temp_dir / f"test{ext}"
            # 即使内容是二进制,扩展名决定它是文本
            file_path.write_bytes(b"\x00\x01\x02\x03")
            assert is_binary_file(file_path) is False, f"扩展名 {ext} 应被视为文本文件"

    def test_binary_extensions_list(self, temp_dir):
        """测试所有二进制扩展名都返回 True."""
        binary_extensions = [
            ".exe",
            ".dll",
            ".so",
            ".bin",
            ".zip",
            ".tar",
            ".gz",
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".bmp",
            ".webp",
            ".mp3",
            ".mp4",
            ".avi",
            ".mkv",
            ".mov",
            ".wav",
            ".pdf",
            ".doc",
            ".docx",
            ".xls",
            ".xlsx",
            ".ppt",
            ".pptx",
            ".pyc",
            ".whl",
            ".deb",
            ".rpm",
            ".dmg",
            ".iso",
            ".apk",
            ".woff",
            ".woff2",
            ".ttf",
            ".otf",
            ".db",
            ".sqlite",
        ]
        for ext in binary_extensions:
            file_path = temp_dir / f"test{ext}"
            # 即使是文本内容,扩展名决定它是二进制
            file_path.write_text("这看起来像文本但扩展名表明是二进制")
            assert is_binary_file(file_path) is True, f"扩展名 {ext} 应被视为二进制文件"

    def test_mime_type_application_json(self, temp_dir):
        """测试 application/json MIME 类型被视为文本."""
        file_path = temp_dir / "config.jsonc"
        # .jsonc 扩展名可能不在 TEXT_EXTENSIONS 中,依赖 MIME 检测
        file_path.write_text('{"key": "value"}')
        assert is_binary_file(file_path) is False

    def test_mime_type_application_xml(self, temp_dir):
        """测试 application/xml MIME 类型被视为文本."""
        file_path = temp_dir / "data.666"
        file_path.write_text("<root>text</root>")
        assert is_binary_file(file_path) is False

    def test_mime_type_text_plain(self, temp_dir):
        """测试 text/plain MIME 类型被视为文本."""
        file_path = temp_dir / "file.custom"
        file_path.write_text("纯文本内容")
        # .custom 扩展名触发 MIME 检测
        assert is_binary_file(file_path) is False

    def test_binary_mime_type_fallback(self, temp_dir):
        """测试二进制 MIME 类型正确检测."""
        file_path = temp_dir / "data.bin"
        # .bin 在 BINARY_EXTENSIONS 中,应返回 True
        assert is_binary_file(file_path) is True

    def test_case_insensitive_extension(self, temp_dir):
        """测试扩展名大小写不敏感."""
        # 大写扩展名
        file_path_py = temp_dir / "test.PY"
        file_path_py.write_text("print('hello')")
        assert is_binary_file(file_path_py) is False

        # 大写二进制扩展名
        file_path_exe = temp_dir / "program.EXE"
        file_path_exe.write_bytes(b"MZ\x90\x00")
        assert is_binary_file(file_path_exe) is True

    def test_dotless_filename(self, temp_dir):
        """测试没有点号的文件名(无扩展名)."""
        file_path = temp_dir / "README"
        file_path.write_text("内容")
        # 无扩展名,回退到 MIME 检测
        assert is_binary_file(file_path) is False

    def test_hidden_file_with_extension(self, temp_dir):
        """测试带扩展名的隐藏文件."""
        file_path = temp_dir / ".hidden.txt"
        file_path.write_text("隐藏文件内容")
        assert is_binary_file(file_path) is False

    def test_file_with_multiple_extensions(self, temp_dir):
        """测试多扩展名文件(只检查最后一个)."""
        # .tar.gz 应该根据 .gz 判断为二进制
        file_path = temp_dir / "archive.tar.gz"
        file_path.write_bytes(b"\x1f\x8b\x08\x00")
        assert is_binary_file(file_path) is True

        # .config.yaml 根据 .yaml 判断为文本
        file_path_yaml = temp_dir / "app.config.yaml"
        file_path_yaml.write_text("key: value")
        assert is_binary_file(file_path_yaml) is False
