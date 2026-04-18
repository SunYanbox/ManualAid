from __future__ import annotations

import tempfile
import unittest

from src.workspace.path_validator import Path, PathNotFoundError, PathValidator, WorkspaceBoundaryError


class TestPathValidator(unittest.TestCase):
    """PathValidator 类的单元测试套件.

    测试工作区路径验证器的核心功能,包括:
    - 相对路径解析和验证
    - 路径遍历攻击防护
    - 符号链接逃逸检测
    - 不存在的路径处理
    """

    def setUp(self):
        """设置测试环境.

        创建临时目录结构:
        - [tmp]/src/app.py
        - 初始化 PathValidator 实例
        """
        self.tmp = tempfile.mkdtemp()
        (Path(self.tmp) / "src").mkdir()
        (Path(self.tmp) / "src" / "app.py").touch()
        self.validator = PathValidator(self.tmp)

    def tearDown(self):
        """清理测试环境.

        递归删除临时目录及其所有内容.
        """
        import shutil

        shutil.rmtree(self.tmp)

    def test_valid_relative_path(self):
        """测试有效的相对路径验证.

        验证:
        1. 相对路径被正确解析为绝对路径
        2. 解析后的路径指向一个真实文件
        """
        res = self.validator.validate("src/app.py")
        self.assertTrue(res.is_absolute())
        self.assertTrue(res.is_file())

    def test_escape_prevention(self):
        """测试路径遍历攻击防护.

        验证使用 '../' 试图逃离工作区的路径会被正确拒绝.
        """
        with self.assertRaises(WorkspaceBoundaryError):
            self.validator.validate("../../etc/passwd")

    def test_symlink_escape(self):
        """测试符号链接逃逸检测.

        验证指向工作区外部的符号链接会被检测并拒绝.
        创建指向 /etc 的符号链接,预期验证器会阻止访问.
        """
        # 创建指向工作区外的符号链接
        link = Path(self.tmp) / "evil_link"
        # 使用绝对路径指向一个明显在工作区外的位置
        outside_path = Path(tempfile.gettempdir()) / "outside_workspace_target"

        try:
            link.symlink_to(outside_path)
            with self.assertRaises(WorkspaceBoundaryError):
                self.validator.validate("evil_link")
        except OSError as e:
            if "WinError 1314" in str(e):
                self.skipTest("Windows 上创建符号链接需要管理员权限")
            raise
        finally:
            # 清理符号链接(如果创建成功)
            if link.exists():
                link.unlink()

    def test_non_existent(self):
        """测试不存在的路径处理.

        验证访问工作区内不存在的路径时会抛出 PathNotFoundError.
        """
        with self.assertRaises(PathNotFoundError):
            self.validator.validate("missing.txt")


if __name__ == "__main__":
    """当脚本直接执行时运行所有测试."""
    unittest.main()
