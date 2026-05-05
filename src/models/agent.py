from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ToolPermissions:
    whitelist: list[str] = field(default_factory=list)
    blacklist: list[str] = field(default_factory=list)

    def is_tool_allowed(self, tool_name: str) -> bool:
        """判定工具是否应注入到 /ws 输出.

        Priority: blacklist first, then whitelist.
        Empty whitelist = allow all.
        """
        if tool_name in self.blacklist:
            return False
        if self.whitelist and tool_name not in self.whitelist:
            return False
        return True


@dataclass
class AgentConfig:
    name: str
    description: str
    tool_permissions: ToolPermissions
    body_role: str = ""
    body_workflow: str = ""
