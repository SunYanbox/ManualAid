import sys
from datetime import date
from pathlib import Path

from src.core.tool_error_response import ToolErrorResponse
from src.workspace.path_validator import PathNotFoundError, PathValidator, WorkspaceBoundaryError


class Workspace:
    def __init__(self, path: str):
        self.root_path = Path(path).resolve()
        self.path_validator: PathValidator = PathValidator(self.root_path)
        self.is_git_repo: bool = (self.root_path / ".git").is_dir()
        self.platform: str = sys.platform
        self.date: str = date.today().strftime("%y-%m-%d")

    def read_file(self, file_path: str, encoding="utf-8") -> str:
        """读取相对于工作区的文件的工具, 只能读取工作区下的文件"""
        try:
            path: Path = self.path_validator.validate(file_path)
            with open(path, encoding=encoding) as f:
                content: str = f.read()
            return content
        except PathNotFoundError as err1:
            return ToolErrorResponse(self.read_file.__name__, err1).to_str()
        except WorkspaceBoundaryError as err2:
            return ToolErrorResponse(self.read_file.__name__, err2).to_str()
        except PermissionError as err3:
            return ToolErrorResponse(self.read_file.__name__, err3).to_str()
        except Exception as err:
            return ToolErrorResponse(self.read_file.__name__, err).to_str()

    def ls(self, folder_path: str = ".") -> list[str] | str:
        """列出指定相对于工作区目录的目录下的所有文件和文件夹路径"""
        try:
            path: Path = self.path_validator.validate(folder_path)
            if not path.is_dir():
                raise ValueError(f"{path} is not a directory")
            return [
                f"{'[Folder]' if item.is_dir() else '[File]'} {item.relative_to(self.root_path)}"
                for item in path.iterdir()
            ]
        except PathNotFoundError as err1:
            return ToolErrorResponse(self.ls.__name__, err1).to_str()
        except WorkspaceBoundaryError as err2:
            return ToolErrorResponse(self.ls.__name__, err2).to_str()
        except PermissionError as err3:
            return ToolErrorResponse(self.ls.__name__, err3).to_str()
        except Exception as err:
            return ToolErrorResponse(self.ls.__name__, err).to_str()

    def glob(self, pattern: str) -> list[str] | str:
        """列出工作区内满足匹配规则的所有文件和文件夹路径"""
        try:
            return [
                f"{'[Folder]' if item.is_dir() else '[File]'} {item.relative_to(self.root_path)}"
                for item in self.root_path.glob(pattern)
            ]
        except PathNotFoundError as err1:
            return ToolErrorResponse(self.glob.__name__, err1).to_str()
        except WorkspaceBoundaryError as err2:
            return ToolErrorResponse(self.glob.__name__, err2).to_str()
        except PermissionError as err3:
            return ToolErrorResponse(self.glob.__name__, err3).to_str()
        except Exception as err:
            return ToolErrorResponse(self.glob.__name__, err).to_str()
