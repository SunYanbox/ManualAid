"""二进制文件保护机制的集成测试.

验证 read/write/edit 工具在遇到二进制文件时的行为:
- read: 返回明确的二进制文件错误提示
- write/edit: 阻止对二进制文件的操作
"""

from pathlib import Path

import pytest

from src.core.database_manager import DatabaseManager
from src.workspace.workspace import Workspace


@pytest.fixture(autouse=True)
def reset_singletons():
    Workspace._instance = None
    DatabaseManager.reset_instances()
    yield
    Workspace._instance = None
    DatabaseManager.reset_instances()


@pytest.fixture
def workspace(tmp_path: Path) -> Workspace:
    ws = Workspace(str(tmp_path))
    return ws


@pytest.fixture
def binary_ext_file(tmp_path: Path) -> Path:
    """创建一个通过扩展名识别的二进制文件."""
    f = tmp_path / "image.png"
    f.write_bytes(b"\x89PNG\r\n\x1a\nfake data")
    return f


@pytest.fixture
def text_file(tmp_path: Path) -> Path:
    """创建一个普通文本文件."""
    f = tmp_path / "readme.txt"
    f.write_text("hello world\nline two", encoding="utf-8")
    return f


class TestReadBinaryProtection:
    """测试 read 工具的二进制保护."""

    def test_read_binary_by_extension(self, workspace: Workspace, binary_ext_file: Path):
        """通过扩展名检测到的二进制文件应被拒绝读取."""
        from src.workspace.tools.read_tool import ReadTool

        tool = ReadTool(workspace)
        result = tool.read("image.png")

        assert "二进制文件" in result

    def test_read_text_file_still_works(self, workspace: Workspace, text_file: Path):
        """文本文件读取应不受影响."""
        from src.workspace.tools.read_tool import ReadTool

        tool = ReadTool(workspace)
        result = tool.read("readme.txt")

        assert "hello world" in result
        assert "二进制文件" not in result


class TestReadRangeBinaryProtection:
    """测试 read 工具按范围读取时的二进制保护."""

    def test_read_range_binary_by_extension(self, workspace: Workspace, binary_ext_file: Path):
        """通过扩展名检测到的二进制文件应被拒绝读取."""
        from src.workspace.tools.read_tool import ReadTool

        tool = ReadTool(workspace)
        result = tool.read("image.png", start=1, end=10)

        assert "二进制文件" in result

    def test_read_range_text_file_still_works(self, workspace: Workspace, text_file: Path):
        """文本文件读取应不受影响."""
        from src.workspace.tools.read_tool import ReadTool

        tool = ReadTool(workspace)
        result = tool.read("readme.txt", start=1, end=2)

        assert "hello world" in result
        assert "二进制文件" not in result


class TestWriteBinaryProtection:
    """测试 write 工具的二进制保护."""

    def test_write_binary_by_extension_blocked(self, workspace: Workspace, binary_ext_file: Path):
        """写入已知二进制扩展名的文件应被阻止."""
        from src.workspace.tools.write_tool import WriteTool

        tool = WriteTool(workspace)
        result = tool.write("image.png", "malicious content")

        assert "二进制文件" in result
        # 不应创建快照
        rows = workspace.db.fetchall("SELECT * FROM file_snapshots")
        assert len(rows) == 0

    def test_write_text_file_still_works(self, workspace: Workspace, text_file: Path):
        """写入文本文件应不受影响."""
        from src.workspace.tools.write_tool import WriteTool

        tool = WriteTool(workspace)
        result = tool.write("readme.txt", "new content")

        assert "Write Preview" in result
        assert "二进制文件" not in result

    def test_write_new_binary_ext_blocked(self, workspace: Workspace):
        """写入新的二进制扩展名文件(不存在)也应被阻止."""
        from src.workspace.tools.write_tool import WriteTool

        tool = WriteTool(workspace)
        result = tool.write("new_app.exe", "fake exe content")

        assert "二进制文件" in result

    def test_write_new_text_ext_allowed(self, workspace: Workspace):
        """写入新的文本扩展名文件应正常通过."""
        from src.workspace.tools.write_tool import WriteTool

        tool = WriteTool(workspace)
        result = tool.write("new_file.py", "print('hello')")

        assert "Write Preview" in result
        assert "二进制文件" not in result


class TestEditBinaryProtection:
    """测试 edit 工具的二进制保护."""

    def test_edit_binary_by_extension_blocked(self, workspace: Workspace, binary_ext_file: Path):
        """编辑已知二进制扩展名的文件应被阻止."""
        from src.workspace.tools.edit_tool import EditTool

        tool = EditTool(workspace)
        result = tool.edit("image.png", "fake", "replaced")

        assert "二进制文件" in result

    def test_edit_text_file_still_works(self, workspace: Workspace, text_file: Path):
        """编辑文本文件应不受影响."""
        from src.workspace.tools.edit_tool import EditTool

        tool = EditTool(workspace)
        result = tool.edit("readme.txt", "hello", "hi")

        assert "Edit Preview" in result
        assert "二进制文件" not in result
