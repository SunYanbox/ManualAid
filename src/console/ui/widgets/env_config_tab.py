from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Input, Label, Static

from src.core.config_manager import DEFAULT_ENVS


class EnvEditDialog(ModalScreen[str | None]):
    """Modal dialog for editing an environment variable value"""

    DEFAULT_CSS = """
    EnvEditDialog {
        align: center middle;
    }

    #env-edit-dialog {
        width: 50;
        height: auto;
        padding: 2;
        border: thick $primary;
        background: $surface;
    }

    #env-edit-dialog > Label {
        text-style: bold;
        margin-bottom: 1;
    }

    .env-edit-field {
        margin-bottom: 1;
    }

    #env-key-display {
        margin-bottom: 1;
        color: $text;
        text-style: bold;
    }

    #env-edit-buttons {
        height: auto;
        align: right middle;
    }

    #env-edit-buttons Button {
        margin-left: 1;
    }
    """

    def __init__(self, key: str = "", value: str = "") -> None:
        super().__init__()
        self._key = key
        self._value = value

    def compose(self):
        with Vertical(id="env-edit-dialog"):
            yield Label("编辑环境变量")
            yield Label("键:", classes="env-edit-field")
            yield Static(self._key, id="env-key-display")
            yield Label("值:", classes="env-edit-field")
            yield Input(value=self._value, id="env-value-input", placeholder="配置值")
            with Horizontal(id="env-edit-buttons"):
                yield Button("取消", id="cancel-btn", variant="default")
                yield Button("确定", id="ok-btn", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "ok-btn":
            value = self.query_one("#env-value-input", Input).value
            self.dismiss(value)
        elif event.button.id == "cancel-btn":
            self.dismiss(None)


class EnvConfigTab(Vertical):
    """环境变量配置标签页.

    显示和编辑预定义的环境变量配置,支持:
    - 查看所有预定义的环境变量
    - 编辑环境变量的值
    - 恢复环境变量为默认值
    - 从 .env 文件读取/写入配置

    注意:不支持添加自定义环境变量,键字段为只读.
    """

    DEFAULT_CSS: ClassVar[str] = """
    EnvConfigTab {
        height: 1fr;
        width: 1fr;
        padding: 0 1;
        overflow-y: auto;
    }

    #env-header {
        height: auto;
        padding: 1 0;
        text-style: bold;
        color: $text;
        border-bottom: solid $primary;
    }

    #env-toolbar {
        height: 1fr;
        padding: 1 0;
        align: left middle;
    }

    #env-toolbar Button {
        margin-right: 1;
    }

    #env-table {
        height: 1fr;
    }

    #env-empty {
        height: 100%;
        content-align: center middle;
        color: $text-muted;
    }

    #env-help {
        height: auto;
        padding: 1;
        margin-top: 1;
        background: $surface;
        border: solid $primary;
        color: $text-muted;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._workspace_root: Path | None = None
        self._env_data: dict[str, str] = {}  # 当前环境变量(包含默认值和用户自定义)
        self._user_envs: dict[str, str] = {}  # 用户在 .env 中的配置

    def compose(self):
        yield Label("环境变量配置", id="env-header")
        with Horizontal(id="env-toolbar"):
            yield Button("编辑", id="env-edit-btn", variant="primary")
            yield Button("恢复默认", id="env-reset-btn", variant="warning")
        yield DataTable(id="env-table")

    def set_workspace_root(self, workspace_root: Path) -> None:
        """设置工作区根目录."""
        self._workspace_root = workspace_root
        self._load_env_file()
        self._refresh()

    def on_mount(self) -> None:
        table = self.query_one("#env-table", DataTable)
        table.add_columns("键", "值", "默认值", "说明")
        table.cursor_type = "row"

    def _load_env_file(self) -> None:
        """从 .env 文件加载环境变量.

        只加载预定义的环境变量,忽略自定义变量.
        """
        self._user_envs.clear()
        self._env_data.clear()

        # 加载默认值
        for key, config in DEFAULT_ENVS.items():
            self._env_data[key] = config["value"]

        # 从 .env 文件加载用户配置(仅限预定义变量)
        if self._workspace_root:
            env_file = self._workspace_root / ".env"
            if env_file.exists():
                try:
                    for line in env_file.read_text(encoding="utf-8").splitlines():
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, _, value = line.partition("=")
                            key = key.strip()
                            value = value.strip().strip('"').strip("'")
                            # 只接受预定义的环境变量
                            if key in DEFAULT_ENVS:
                                self._user_envs[key] = value
                                self._env_data[key] = value
                except Exception:
                    pass

    def _save_env_file(self) -> None:
        """保存非默认值到 .env 文件.

        只保存预定义变量中与默认值不同的配置.
        """
        if not self._workspace_root:
            return

        env_file = self._workspace_root / ".env"

        # 只保存与默认值不同的预定义变量
        non_default = {}
        for key, value in self._env_data.items():
            if key in DEFAULT_ENVS:
                default_config = DEFAULT_ENVS[key]
                if value != default_config["value"]:
                    non_default[key] = value

        try:
            if non_default:
                lines = ["# ManualAid 环境变量配置\n"]
                for key, value in sorted(non_default.items()):
                    lines.append(f"{key}={value}\n")
                env_file.write_text("".join(lines), encoding="utf-8")
            elif env_file.exists():
                # 如果所有值都是默认值,删除 .env 文件
                env_file.unlink()
        except Exception as e:
            self.notify(f"保存失败: {e}", severity="error")

    def _refresh(self) -> None:
        """刷新环境变量列表.

        只显示预定义的环境变量.
        """
        table = self.query_one("#env-table", DataTable)
        table.clear()

        # 只显示预定义的环境变量
        for key, config in DEFAULT_ENVS.items():
            value = self._env_data.get(key, config["value"])
            default_value = config["value"]
            desc = config["description"]
            table.add_row(key, value, default_value, desc)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id or ""

        if button_id == "env-edit-btn":
            table = self.query_one("#env-table", DataTable)
            if table.cursor_row is None or table.cursor_row < 0:
                self.notify("请先选择一行", severity="warning")
                return

            row_data = table.get_row_at(table.cursor_row)
            if row_data:
                key, value, _, _ = row_data
                self.app.push_screen(EnvEditDialog(key=key, value=value), self._on_edit_result)

        elif button_id == "env-reset-btn":
            # 重置选中行为默认值
            table = self.query_one("#env-table", DataTable)
            if table.cursor_row is None or table.cursor_row < 0:
                self.notify("请先选择一行", severity="warning")
                return

            row_data = table.get_row_at(table.cursor_row)
            if row_data:
                key = row_data[0]
                if key in DEFAULT_ENVS:
                    self._env_data[key] = DEFAULT_ENVS[key]["value"]
                    if key in self._user_envs:
                        del self._user_envs[key]
                    self._save_env_file()
                    self._refresh()
                    self.notify(f"已恢复默认值: {key}")

    def _on_edit_result(self, result: str | None) -> None:
        """处理编辑对话框的结果.

        Args:
            result: 编辑后的值,或 None 表示取消
        """
        if result is not None:
            table = self.query_one("#env-table", DataTable)
            if table.cursor_row is not None and table.cursor_row >= 0:
                row_data = table.get_row_at(table.cursor_row)
                if row_data:
                    key = row_data[0]
                    self._env_data[key] = result
                    self._user_envs[key] = result
                    self._save_env_file()
                    self._refresh()
                    self.notify(f"已更新: {key}")
