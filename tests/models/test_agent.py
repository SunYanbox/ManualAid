"""Tests for agent data models."""

from src.models.agent import AgentConfig, ToolPermissions


def test_empty_permissions_allow_all():
    p = ToolPermissions()
    assert p.is_tool_allowed("read")
    assert p.is_tool_allowed("write")
    assert p.is_tool_allowed("git")
    # Explicit empty lists are equivalent to no arguments
    p2 = ToolPermissions(whitelist=[], blacklist=[])
    assert p2.is_tool_allowed("anything")


def test_whitelist_restricts_tools():
    p = ToolPermissions(whitelist=["read", "glob", "ls"])
    assert p.is_tool_allowed("read")
    assert p.is_tool_allowed("glob")
    assert not p.is_tool_allowed("write")
    assert not p.is_tool_allowed("git")


def test_blacklist_blocks_tools():
    p = ToolPermissions(blacklist=["git"])
    assert not p.is_tool_allowed("git")
    assert p.is_tool_allowed("read")


def test_blacklist_overrides_whitelist():
    p = ToolPermissions(whitelist=["read", "git"], blacklist=["git"])
    assert p.is_tool_allowed("read")
    assert not p.is_tool_allowed("git")


def test_agent_config_creation():
    """Verify AgentConfig stores fields correctly."""
    perms = ToolPermissions(whitelist=["read", "glob"])
    agent = AgentConfig(
        name="test-agent",
        description="A test agent",
        tool_permissions=perms,
        body_role="## Role\nYou are a test agent.",
        body_workflow="## Workflow\n1. Do work.",
    )
    assert agent.name == "test-agent"
    assert agent.description == "A test agent"
    assert agent.tool_permissions is perms
    assert "You are a test agent." in agent.body_role
    assert "Do work." in agent.body_workflow


def test_agent_config_defaults():
    """Verify AgentConfig defaults are empty strings."""
    agent = AgentConfig(name="minimal", description="Minimal", tool_permissions=ToolPermissions())
    assert agent.body_role == ""
    assert agent.body_workflow == ""
    assert agent.tool_permissions.whitelist == []
    assert agent.tool_permissions.blacklist == []
