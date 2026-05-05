"""Tests for agent data models."""

from src.models.agent import ToolPermissions


def test_empty_permissions_allow_all():
    p = ToolPermissions()
    assert p.is_tool_allowed("read")
    assert p.is_tool_allowed("write")
    assert p.is_tool_allowed("git")


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


def test_whitelist_empty_is_no_restriction():
    """Empty whitelist means 'no whitelist restriction' — all tools pass."""
    p = ToolPermissions(whitelist=[], blacklist=[])
    assert p.is_tool_allowed("anything")


def test_whitelist_and_blacklist_both_empty():
    p = ToolPermissions()
    assert p.is_tool_allowed("any_tool")
