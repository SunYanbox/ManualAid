from __future__ import annotations

from pathlib import Path
from typing import ClassVar

from textual.containers import Vertical
from textual.widgets import TabbedContent, TabPane

from src.console.ui.widgets.env_config_tab import EnvConfigTab
from src.console.ui.widgets.skill_config_tab import SkillConfigTab


class SettingsTab(Vertical):
    """设置标签页.

    包含多个子标签页:
    - 环境变量配置
    - Skill 配置
    """

    DEFAULT_CSS: ClassVar[str] = """
    SettingsTab {
        height: 1fr;
        width: 1fr;
        padding: 0;
    }

    SettingsTab TabbedContent {
        height: 1fr;
    }

    SettingsTab TabbedContent > TabPane {
        padding: 0;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._workspace_root: Path | None = None
        self._skill_manager = None

    def compose(self):
        with TabbedContent():
            with TabPane("环境变量", id="tab-env"):
                yield EnvConfigTab()
            with TabPane("Skills", id="tab-skills"):
                yield SkillConfigTab()

    def on_mount(self) -> None:
        """初始化子标签页."""
        pass

    def set_managers(self, workspace_root: Path, skill_manager) -> None:
        """设置工作区根目录和管理器."""
        self._workspace_root = workspace_root
        self._skill_manager = skill_manager

        # 传递给环境变量配置
        env_tab = self.query_one(EnvConfigTab)
        env_tab.set_workspace_root(workspace_root)

        # 传递给 Skill 配置
        skill_tab = self.query_one(SkillConfigTab)
        skill_tab.set_managers(skill_manager, workspace_root)

    @property
    def env_config_tab(self) -> EnvConfigTab:
        return self.query_one(EnvConfigTab)

    @property
    def skill_config_tab(self) -> SkillConfigTab:
        return self.query_one(SkillConfigTab)
