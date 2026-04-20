from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.workspace.workspace import Workspace


class TestWorkspace(unittest.TestCase):
    """Workspace 类的单元测试套件.

    测试工作区工具的核心功能,包括:
    - 工作区初始化
    - 文件读取
    - 目录列表
    - 文件模式匹配
    """

    def setUp(self):
        """设置测试环境.

        创建临时目录结构:
        - [tmp]/src/app.py
        - [tmp]/src/subdir/file.txt
        - [tmp]/test.txt
        """
        self.tmp = tempfile.mkdtemp()
        self.root = Path(self.tmp)

        # 创建测试文件结构
        (self.root / "src").mkdir()
        (self.root / "src" / "app.py").write_text("print('Hello World')")

        (self.root / "src" / "subdir").mkdir()
        (self.root / "src" / "subdir" / "file.txt").write_text("Test content")

        (self.root / "test.txt").write_text("Root file")

        self.workspace = Workspace(str(self.root))

    def tearDown(self):
        """清理测试环境.

        递归删除临时目录及其所有内容.
        """
        import shutil

        shutil.rmtree(self.tmp)

    def test_initialization(self):
        """测试工作区初始化."""
        self.assertEqual(self.workspace.root_path, self.root.resolve())
        self.assertFalse(self.workspace.is_git_repo)
        self.assertIsInstance(self.workspace.platform, str)
        self.assertIsInstance(self.workspace.date, str)

    def test_read_file_valid(self):
        """测试读取有效的文件."""
        content = self.workspace.read_file("test.txt")
        self.assertEqual(content, "Root file")

        content = self.workspace.read_file("src/app.py")
        self.assertEqual(content, "print('Hello World')")

    def test_read_file_not_found(self):
        """测试读取不存在的文件."""
        result = self.workspace.read_file("missing.txt")
        self.assertIsInstance(result, str)
        self.assertIn("tool_name=read_file", result)
        self.assertIn("PathNotFoundError", result)

    def test_read_file_outside_workspace(self):
        """测试读取工作区外的文件."""
        result = self.workspace.read_file("../../etc/passwd")
        self.assertIsInstance(result, str)
        self.assertIn("tool_name=read_file", result)
        self.assertIn("WorkspaceBoundaryError", result)

    def test_ls_current_directory(self):
        """测试列出当前目录."""
        result = self.workspace.ls()
        self.assertIsInstance(result, list)
        self.assertTrue(any("[File] test.txt" in str(item) for item in result))
        self.assertTrue(any("[Folder] src" in str(item) for item in result))

    def test_ls_specific_directory(self):
        """测试列出指定目录."""
        result = self.workspace.ls("src")
        self.assertIsInstance(result, list)
        # Check for expected format - the format is [Folder/File] relative_path
        found_file = False
        found_folder = False
        for item in result:
            item_str = str(item)
            # The format is [File] src/app.py or [Folder] src/subdir
            if "app.py" in item_str:
                found_file = True
            if "subdir" in item_str:
                found_folder = True
        self.assertTrue(found_file)
        self.assertTrue(found_folder)

    def test_ls_not_directory(self):
        """测试列出非目录路径."""
        result = self.workspace.ls("test.txt")
        self.assertIsInstance(result, str)
        self.assertIn("tool_name=read_file", result)

    def test_ls_outside_workspace(self):
        """测试列出工作区外的目录."""
        result = self.workspace.ls("../../etc")
        self.assertIsInstance(result, str)
        self.assertIn("tool_name=read_file", result)
        self.assertIn("WorkspaceBoundaryError", result)

    def test_glob_pattern(self):
        """测试文件模式匹配."""
        result = self.workspace.glob("**/*.txt")
        self.assertIsInstance(result, list)
        self.assertTrue(any("test.txt" in str(item) for item in result))
        self.assertTrue(any("file.txt" in str(item) for item in result))

    def test_glob_no_matches(self):
        """测试没有匹配的模式."""
        result = self.workspace.glob("*.md")
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)

    def test_glob_invalid_pattern(self):
        """测试无效模式.

        注意: glob 函数使用异常处理但返回的是空列表而不是错误字符串
        """
        result = self.workspace.glob("[invalid")
        # glob 函数返回空列表而不是错误字符串
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)


if __name__ == "__main__":
    """当脚本直接执行时运行所有测试."""
    unittest.main()
