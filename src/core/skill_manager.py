"""Skill 发现和管理服务."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import ClassVar

from src.models.skill import SkillInfo


class SkillManager:
    """Skill 发现和管理服务(单例模式).

    负责从多个位置发现 Skill,并提供查询和加载功能.
    """

    _instance: ClassVar[SkillManager | None] = None
    _instance_lock: ClassVar[threading.Lock] = threading.Lock()

    # Skill 发现路径模板
    GLOBAL_PATHS: ClassVar[list[str]] = [
        "~/.claude/skills",
        "~/.agents/skills",
    ]

    PROJECT_PATHS: ClassVar[list[str]] = [
        ".claude/skills",
        ".agents/skills",
        ".ManualAid/skills",
        ".opencode/skill",
        ".opencode/skills",
    ]

    def __new__(cls) -> SkillManager:
        with cls._instance_lock:
            if cls._instance is None:
                instance = super().__new__(cls)
                instance._initialized = False
                cls._instance = instance
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return

        self._skills: dict[str, SkillInfo] = {}
        self._disabled_skills: set[str] = set()
        self._workspace_root: Path | None = None
        self._initialized = True

    def discover(self, workspace_root: Path | None = None) -> dict[str, SkillInfo]:
        """发现所有可用的 Skill.

        Args:
            workspace_root: 工作区根目录,用于发现项目级 Skill

        Returns:
            Skill 名称到 SkillInfo 的映射
        """
        self._skills.clear()
        self._workspace_root = workspace_root

        # 1. 从数据库加载禁用的 Skill 列表
        if workspace_root:
            self._load_disabled_from_db(workspace_root)

        # 2. 发现全局 Skill
        for path_template in self.GLOBAL_PATHS:
            skills_dir = Path(path_template).expanduser()
            if skills_dir.is_dir():
                self._discover_in_dir(skills_dir, is_global=True)

        # 3. 发现项目级 Skill
        if workspace_root:
            for relative_path in self.PROJECT_PATHS:
                skills_dir = workspace_root / relative_path
                if skills_dir.is_dir():
                    self._discover_in_dir(skills_dir, is_global=False)

        return self._skills

    def _load_disabled_from_db(self, workspace_root: Path) -> None:
        """从数据库加载禁用的 Skill 列表.

        Args:
            workspace_root: 工作区根目录
        """
        try:
            from src.core.database_manager import DatabaseManager

            db = DatabaseManager(str(workspace_root))
            self._disabled_skills = db.get_disabled_skills()
        except Exception:
            self._disabled_skills = set()

    def save_disabled_to_db(self, workspace_root: Path | None = None) -> None:
        """保存禁用的 Skill 列表到数据库.

        Args:
            workspace_root: 工作区根目录,如果为 None 则使用缓存的值
        """
        root = workspace_root or self._workspace_root
        if root is None:
            return

        try:
            from src.core.database_manager import DatabaseManager

            db = DatabaseManager(str(root))
            db.set_disabled_skills(self._disabled_skills)
        except Exception:
            pass

    def _discover_in_dir(self, skills_dir: Path, is_global: bool = True) -> None:
        """在指定目录中发现 Skill.

        Args:
            skills_dir: Skill 目录
            is_global: 是否为全局目录
        """
        try:
            for item in skills_dir.iterdir():
                if item.is_dir():
                    skill_info = SkillInfo.from_dir(item)
                    if skill_info:
                        skill_info.metadata["is_global"] = is_global
                        # 如果已存在同名 Skill,项目级覆盖全局
                        if skill_info.name in self._skills:
                            existing = self._skills[skill_info.name]
                            # 项目级优先
                            if not existing.metadata.get("is_global", True):
                                continue
                        # 应用禁用状态
                        if skill_info.name in self._disabled_skills:
                            skill_info.enabled = False
                        self._skills[skill_info.name] = skill_info
        except Exception:
            pass

    def get(self, name: str) -> SkillInfo | None:
        """获取指定名称的 Skill.

        Args:
            name: Skill 名称

        Returns:
            SkillInfo 实例,如果不存在则返回 None
        """
        return self._skills.get(name)

    def get_all(self) -> dict[str, SkillInfo]:
        """获取所有 Skill.

        Returns:
            Skill 名称到 SkillInfo 的映射
        """
        return self._skills.copy()

    def get_enabled(self) -> dict[str, SkillInfo]:
        """获取所有启用的 Skill.

        Returns:
            Skill 名称到 SkillInfo 的映射
        """
        return {name: skill for name, skill in self._skills.items() if skill.enabled}

    def set_disabled(self, names: set[str], persist: bool = True) -> None:
        """设置禁用的 Skill 列表.

        Args:
            names: 要禁用的 Skill 名称集合
            persist: 是否持久化到数据库
        """
        self._disabled_skills = names.copy()
        for skill in self._skills.values():
            skill.enabled = skill.name not in self._disabled_skills

        if persist:
            self.save_disabled_to_db()

    def get_disabled(self) -> set[str]:
        """获取禁用的 Skill 名称集合.

        Returns:
            禁用的 Skill 名称集合
        """
        return self._disabled_skills.copy()

    def format_skills_list(self, verbose: bool = False) -> str:
        """格式化 Skill 列表为字符串.

        Args:
            verbose: 是否输出详细信息

        Returns:
            格式化后的字符串
        """
        if not self._skills:
            return "No skills available."

        if verbose:
            lines = ["<available_skills>"]
            for skill in sorted(self._skills.values(), key=lambda s: s.name):
                lines.append("  <skill>")
                lines.append(f"    <name>{skill.name}</name>")
                lines.append(f"    <description>{skill.description}</description>")
                lines.append("  </skill>")
            lines.append("</available_skills>")
            return "\n".join(lines)
        else:
            lines = ["## Available Skills"]
            for skill in sorted(self._skills.values(), key=lambda s: s.name):
                status = "" if skill.enabled else " [DISABLED]"
                lines.append(f"- **{skill.name}**: {skill.description}{status}")
            return "\n".join(lines)

    def load_skill_content(self, name: str) -> str | None:
        """加载 Skill 的完整内容(用于注入到提示词).

        Args:
            name: Skill 名称

        Returns:
            Skill 内容字符串,如果不存在则返回 None
        """
        skill = self.get(name)
        if not skill:
            return None

        lines = [
            f'<skill_content name="{skill.name}">',
            f"# Skill: {skill.name}",
            "",
            skill.content.strip(),
            "",
            f"Base directory for this skill: {skill.location}",
            "<skill_files>",
        ]

        for filename in skill.files:
            lines.append(f"  - {filename}")

        lines.append("</skill_files>")
        lines.append("</skill_content>")

        return "\n".join(lines)

    @classmethod
    def reset_instance(cls) -> None:
        """重置单例实例(用于测试)."""
        with cls._instance_lock:
            if cls._instance is not None:
                cls._instance._skills.clear()
                cls._instance._disabled_skills.clear()
                cls._instance._workspace_root = None
                cls._instance = None
