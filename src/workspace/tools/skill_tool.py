"""Skill 工具实现."""

from __future__ import annotations

from src.models.tools.tool_result import ToolResult
from src.workspace.tools.base_tool import BaseTool
from src.workspace.workspace import Workspace


class SkillTool(BaseTool):
    """Skill 加载工具.

    用于加载指定的 Skill 并将其内容注入到当前会话中.
    """

    def __init__(self, workspace: Workspace) -> None:
        super().__init__(
            workspace=workspace,
            name="skill",
            doc="当**当前任务**与系统提示中列出的某一技能相匹配时, 加载该专业技能"
            "使用此工具将技能的指令和资源注入当前对话.输出内容可能包含详细的工作流程指导, "
            "以及对该技能所在目录中的脚本、文件等的引用"
            "技能名称必须与系统提示中列出的某一技能完全一致",
            read_permission=True,
            write_permission=False,
        )
        self.func = self._execute
        self.params = self.extract_params(self._execute)
        self.param_descriptions = {
            "name": "The name of the skill from available_skills",
        }

    def _execute(self, name: str) -> ToolResult:
        """执行 Skill 加载.

        Args:
            name: Skill 名称

        Returns:
            ToolResult 包含 Skill 内容或错误信息
        """
        from src.core.skill_manager import SkillManager

        skill_manager = SkillManager()

        # 确保 Skill 已发现
        if not skill_manager.get_all():
            skill_manager.discover(self.workspace.root_path)

        skill = skill_manager.get(name)

        if skill is None:
            return self.make_failed_response(
                kwargs={"name": name},
                error=f'Skill "{name}" not found. Use a skill name from the available_skills list.',
            )

        if not skill.enabled:
            return self.make_failed_response(
                kwargs={"name": name},
                error=f'Skill "{name}" is disabled. Enable it in the configuration.',
            )

        content = skill_manager.load_skill_content(name)

        if content is None:
            return self.make_failed_response(
                kwargs={"name": name},
                error=f'Failed to load skill "{name}".',
            )

        return self.make_success_response(
            kwargs={"name": name},
            data={"title": f"Loaded skill: {name}", "output": content},
        )
