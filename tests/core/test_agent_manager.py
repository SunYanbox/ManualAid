"""Tests for AgentManager and frontmatter parser."""

from pathlib import Path

from src.core.agent_manager import AgentManager, _parse_agent_file, _parse_frontmatter


class TestParseFrontmatter:
    def test_no_frontmatter(self):
        content = "## Role\nhello"
        meta, body = _parse_frontmatter(content)
        assert meta == {}
        assert "hello" in body

    def test_basic_frontmatter(self):
        content = """---
name: test-agent
description: A test agent
---
## Role
Hello World
"""
        meta, body = _parse_frontmatter(content)
        assert meta["name"] == "test-agent"
        assert meta["description"] == "A test agent"
        assert "Hello World" in body

    def test_permissions_frontmatter(self):
        content = """---
name: restricted
description: Restricted agent
tool_permissions:
  whitelist:
    - read
    - glob
  blacklist:
    - git
---
## Role
test
"""
        meta, _body = _parse_frontmatter(content)
        assert meta["tool_permissions.whitelist"] == ["read", "glob"]
        assert meta["tool_permissions.blacklist"] == ["git"]

    def test_empty_permissions(self):
        content = """---
name: empty
description: Empty perms
tool_permissions:
  whitelist: []
  blacklist: []
---
## Role
test
"""
        meta, _body = _parse_frontmatter(content)
        whitelist = meta.get("tool_permissions.whitelist", [])
        blacklist = meta.get("tool_permissions.blacklist", [])
        assert whitelist == [], f"Expected [], got {whitelist!r}"
        assert blacklist == [], f"Expected [], got {blacklist!r}"


class TestParseAgentFile:
    def test_full_agent_file(self, tmp_path: Path):
        md_file = tmp_path / "test-agent.md"
        md_file.write_text(
            """---
name: test-agent
description: My test agent
tool_permissions:
  whitelist:
    - read
    - glob
  blacklist:
    - git
---

## Role

You are a test agent.

## Workflow

1. Test things.
2. Verify results.
""",
            encoding="utf-8",
        )
        agent = _parse_agent_file(md_file)
        assert agent is not None
        assert agent.name == "test-agent"
        assert agent.description == "My test agent"
        assert agent.tool_permissions.whitelist == ["read", "glob"]
        assert agent.tool_permissions.blacklist == ["git"]
        assert "You are a test agent." in agent.body_role
        assert "Test things." in agent.body_workflow

    def test_invalid_file_returns_none(self, tmp_path: Path):
        md_file = tmp_path / "invalid.md"
        md_file.write_bytes(b"\x80\x81\x82")  # invalid UTF-8
        agent = _parse_agent_file(md_file)
        assert agent is None

    def test_no_role_section(self, tmp_path: Path):
        md_file = tmp_path / "no-role.md"
        md_file.write_text(
            """---
name: no-role
description: No role
---
Some content without sections.
""",
            encoding="utf-8",
        )
        agent = _parse_agent_file(md_file)
        assert agent is not None
        assert agent.body_role == ""
        assert agent.body_workflow == ""


class TestAgentManager:
    def test_get_default_fallback(self, tmp_path):
        """No agents dir -> get_default() returns a fallback AgentConfig."""
        mgr = AgentManager()
        mgr.initialize(tmp_path)
        default = mgr.get_default()
        assert default.name == "default"
        assert default.tool_permissions.whitelist == []

    def test_switch_unknown_returns_false(self, tmp_path):
        mgr = AgentManager()
        mgr.initialize(tmp_path)
        assert mgr.switch_agent("nonexistent") is False

    def test_write_default_creates_file(self, tmp_path):
        mgr = AgentManager()
        mgr.initialize(tmp_path)
        mgr.write_default(tmp_path)
        agents_dir = tmp_path / ".ManualAid" / "agents"
        assert (agents_dir / "default.md").exists()

    def test_write_default_is_idempotent(self, tmp_path):
        mgr = AgentManager()
        mgr.initialize(tmp_path)
        mgr.write_default(tmp_path)
        content_first = (tmp_path / ".ManualAid" / "agents" / "default.md").read_text(encoding="utf-8")
        mgr.write_default(tmp_path)  # second call should be no-op
        content_second = (tmp_path / ".ManualAid" / "agents" / "default.md").read_text(encoding="utf-8")
        assert content_first == content_second

    def test_agent_names_sorted(self, tmp_path):
        agents_dir = tmp_path / ".ManualAid" / "agents"
        agents_dir.mkdir(parents=True)
        (agents_dir / "z-agent.md").write_text("---\nname: z-agent\ndescription: Z\n---\n## Role\nx")
        (agents_dir / "a-agent.md").write_text("---\nname: a-agent\ndescription: A\n---\n## Role\nx")
        mgr = AgentManager()
        mgr.initialize(tmp_path)
        assert mgr.agent_names() == ["a-agent", "z-agent"]
