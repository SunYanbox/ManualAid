"""Agent manager — singleton, loads and manages agent configurations."""

from __future__ import annotations

import threading
import warnings
from pathlib import Path

from src.constants.manual_aid import AGENTS_DIR, MANUALAID_DIR
from src.models.agent import AgentConfig, ToolPermissions

# ---------------------------------------------------------------------------
# Frontmatter parser (YAML subset: key:value, nested keys, dash lists)
# ---------------------------------------------------------------------------


def _parse_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML frontmatter delimited by --- markers.

    Returns (metadata_dict, body_string). Only supports:
    - key: value pairs (strings)
    - nested keys via indentation (2-space)
    - dash list items under nested keys

    Non-goal: not a full YAML parser; only the subset needed for agent configs.
    """
    lines = content.split("\n")
    if not lines or lines[0].strip() != "---":
        return {}, content

    end_idx = -1
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break

    if end_idx == -1:
        return {}, content

    frontmatter_lines = lines[1:end_idx]
    body = "\n".join(lines[end_idx + 1 :]).strip()

    metadata: dict = {}
    current_section: str | None = None
    current_subsection: str | None = None

    for line in frontmatter_lines:
        stripped = line.rstrip()
        if not stripped.strip():
            continue

        indent = len(line) - len(line.lstrip())

        if stripped.lstrip().startswith("- ") and current_subsection:
            item = stripped.lstrip()[2:].strip()
            if item:
                metadata.setdefault(current_subsection, []).append(item)
        elif ":" in stripped:
            parts = stripped.split(":", 1)
            key = parts[0].strip()
            value = parts[1].strip() if len(parts) > 1 and parts[1].strip() else ""

            if indent == 0:
                current_section = key
                current_subsection = None
                if value:
                    metadata[key] = value
            elif indent > 0 and current_section:
                qualified = f"{current_section}.{key}"
                if value and value != "[]":
                    metadata[qualified] = value
                    current_subsection = None
                else:
                    current_subsection = qualified if value != "[]" else None

    return metadata, body


def _parse_agent_file(file_path: Path) -> AgentConfig | None:
    """Parse a single agent .md file into an AgentConfig."""
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        warnings.warn(f"Failed to read agent file {file_path}: {e}", stacklevel=2)
        return None

    metadata, body = _parse_frontmatter(content)

    name = metadata.get("name", file_path.stem)
    description = metadata.get("description", "")

    # Parse tool permissions — handle both list and empty-list cases
    raw_whitelist = metadata.get("tool_permissions.whitelist", [])
    raw_blacklist = metadata.get("tool_permissions.blacklist", [])
    if isinstance(raw_whitelist, str):
        raw_whitelist = [raw_whitelist] if raw_whitelist else []
    if isinstance(raw_blacklist, str):
        raw_blacklist = [raw_blacklist] if raw_blacklist else []

    tool_permissions = ToolPermissions(
        whitelist=raw_whitelist,
        blacklist=raw_blacklist,
    )

    # Parse ## Role and ## Workflow sections from body
    body_role = ""
    body_workflow = ""
    current_heading: str | None = None
    section_lines: list[str] = []

    for line in body.split("\n"):
        if line.startswith("## "):
            # Save previous section
            heading_text = line[3:].strip().lower()
            joined = "\n".join(section_lines).strip()
            if current_heading == "role":
                body_role = joined
            elif current_heading == "workflow":
                body_workflow = joined

            current_heading = heading_text if heading_text in ("role", "workflow") else None
            section_lines = [line]
        elif current_heading:
            section_lines.append(line)
        else:
            section_lines = []

    # Save last section
    joined = "\n".join(section_lines).strip()
    if current_heading == "role":
        body_role = joined
    elif current_heading == "workflow":
        body_workflow = joined

    return AgentConfig(
        name=name,
        description=description,
        tool_permissions=tool_permissions,
        body_role=body_role,
        body_workflow=body_workflow,
    )


# ---------------------------------------------------------------------------
# Agent Manager (singleton)
# ---------------------------------------------------------------------------


class AgentManager:
    """Singleton — loads and caches agent configurations from .ManualAid/agents/.

    Usage:
        mgr = AgentManager()
        mgr.initialize(workspace_root)
        mgr.write_default(workspace_root)
        agent = mgr.get_current()
    """

    _instance: AgentManager | None = None
    _instance_lock: threading.Lock = threading.Lock()

    def __new__(cls) -> AgentManager:
        with cls._instance_lock:
            if cls._instance is None:
                instance = super().__new__(cls)
                instance._initialized = False
                cls._instance = instance
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._agents: dict[str, AgentConfig] = {}
        self._agents_dir: Path | None = None
        self._loaded = False
        self._load_lock: threading.Lock = threading.Lock()
        self._current_agent_name: str = "default"
        self._initialized = True

    @property
    def current_agent_name(self) -> str:
        return self._current_agent_name

    @current_agent_name.setter
    def current_agent_name(self, value: str) -> None:
        self._current_agent_name = value

    def initialize(self, root_path: str | Path) -> None:
        """Set the workspace root. Agents are loaded lazily on first access."""
        self._agents_dir = Path(root_path) / MANUALAID_DIR / AGENTS_DIR
        self._loaded = False
        self._agents = {}

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        with self._load_lock:
            if self._loaded:
                return
            self._agents = {}
            if self._agents_dir and self._agents_dir.is_dir():
                for fpath in sorted(self._agents_dir.glob("*.md")):
                    agent = _parse_agent_file(fpath)
                    if agent is not None:
                        self._agents[agent.name] = agent
            self._loaded = True

    def get(self, name: str) -> AgentConfig | None:
        self._ensure_loaded()
        return self._agents.get(name)

    def get_default(self) -> AgentConfig:
        self._ensure_loaded()
        default = self._agents.get("default")
        if default is None:
            return AgentConfig(
                name="default",
                description="Default agent",
                tool_permissions=ToolPermissions(),
            )
        return default

    def get_current(self) -> AgentConfig:
        agent = self.get(self._current_agent_name)
        return agent if agent is not None else self.get_default()

    def switch_agent(self, name: str) -> bool:
        self._ensure_loaded()
        if name in self._agents:
            self._current_agent_name = name
            return True
        return False

    def list_agents(self) -> list[AgentConfig]:
        self._ensure_loaded()
        return list(self._agents.values())

    def agent_names(self) -> list[str]:
        self._ensure_loaded()
        return sorted(self._agents.keys())

    def write_default(self, root_path: str | Path) -> None:
        """Write the default.md agent file if it does not exist.

        Content mirrors the prompts.py SYSTEM_IDENTITY and WORKFLOW_GUIDELINES
        so that users can edit language/behavior by modifying this file.
        """
        agents_dir = Path(root_path) / MANUALAID_DIR / AGENTS_DIR
        agents_dir.mkdir(parents=True, exist_ok=True)
        default_path = agents_dir / "default.md"
        if default_path.exists():
            return

        content = r"""---
name: default
description: Default ManualAid agent
tool_permissions:
  whitelist: []
  blacklist: []
---

## Role

你是一个与 ManualAid 工作区集成的、依赖工具进行文件探索和编辑的助手.
你的能力来源于工作区提供的工具——如果没有调用正确的工具,你无法独立行动.

<constraints>
  <constraint>你是一个依赖工具的助手.你不能独立行动;必须调用工具来完成任务</constraint>
  <constraint>严格使用指定的 XML 格式来调用工具(见 &lt;tool_rules&gt;)</constraint>
  <constraint>调用工具后,始终停止并等待用户的工具输出</constraint>
  <constraint>绝不虚构工具返回值.绝不臆测结果继续</constraint>
  <constraint>如果工具调用失败或返回空,向用户请求澄清</constraint>
</constraints>

## Workflow

1. 在采取行动前充分理解用户的请求.如有疑问,先提问再行动.
2. 将复杂或多步骤任务分解为较小的顺序子任务;一次一个步骤.
3. 为每个步骤选择最合适的工具.如果没有合适的工具,解释并请求替代方案.
4. 等待每个工具的结果后再继续下一步.
5. 构建响应时,先使用工具收集信息,然后形成最终答案.
"""
        default_path.write_text(content, encoding="utf-8")
