"""Skill 数据模型."""

from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class SkillInfo:
    """Skill 信息模型.

    Attributes:
        name: Skill 名称(来自目录名)
        description: Skill 描述(来自 SKILL.md 第一行或 skill.txt)
        location: Skill 所在目录的绝对路径
        content: SKILL.md 的完整内容
        files: Skill 目录中的其他文件列表(排除 SKILL.md)
        enabled: 是否启用(用于配置)
    """

    name: str
    description: str = ""
    location: str = ""
    content: str = ""
    files: list[str] = field(default_factory=list)
    enabled: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dir(cls, skill_dir: Path) -> SkillInfo | None:
        """从目录加载 Skill 信息.

        Args:
            skill_dir: Skill 目录路径

        Returns:
            SkillInfo 实例,如果目录无效则返回 None
        """
        skill_md = skill_dir / "SKILL.md"
        skill_txt = skill_dir / "skill.txt"

        # 必须有 SKILL.md 文件
        if not skill_md.exists():
            return None

        try:
            content = skill_md.read_text(encoding="utf-8")
        except Exception:
            return None

        # 解析 YAML frontmatter
        name = skill_dir.name  # 默认使用目录名
        description = ""

        if content.startswith("---"):
            # 解析 YAML frontmatter
            parts = content.split("---", 2)
            if len(parts) >= 3:
                try:
                    frontmatter = yaml.safe_load(parts[1])
                    if frontmatter:
                        name = frontmatter.get("name", name)
                        description = frontmatter.get("description", "")
                except Exception:
                    pass

        # 如果没有从 frontmatter 获取到描述,尝试其他方式
        if not description:
            # 优先从 skill.txt
            if skill_txt.exists():
                with suppress(Exception):
                    description = skill_txt.read_text(encoding="utf-8").strip()

            if not description:
                # 从 SKILL.md 第一行提取标题
                first_line = content.split("\n")[0] if content else ""
                if first_line.startswith("#"):
                    description = first_line.lstrip("#").strip()
                else:
                    description = first_line.strip() or skill_dir.name

        # 收集其他文件
        files: list[str] = []
        try:
            for f in skill_dir.iterdir():
                if f.is_file() and f.name not in ("SKILL.md", "skill.txt"):
                    files.append(f.name)
        except Exception:
            pass

        return cls(
            name=name,
            description=description,
            location=str(skill_dir),
            content=content,
            files=sorted(files),
            enabled=True,
        )

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式."""
        return {
            "name": self.name,
            "description": self.description,
            "location": self.location,
            "files": self.files,
            "enabled": self.enabled,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SkillInfo:
        """从字典创建实例."""
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            location=data.get("location", ""),
            content=data.get("content", ""),
            files=data.get("files", []),
            enabled=data.get("enabled", True),
            metadata=data.get("metadata", {}),
        )
