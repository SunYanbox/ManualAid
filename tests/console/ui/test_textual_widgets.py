from __future__ import annotations

import asyncio
import re
from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.widgets import Button, Collapsible, Static

from src.console.ui.repl import REPL
from src.console.ui.widgets.collapsible_helper import make_collapsible_with_copy_button
from src.console.ui.widgets.tools_result_widget import ToolsResultWidget
from src.models.tools.tool_result_collection import ToolResultCollection


def _css_block(css: str, selector: str) -> str:
    match = re.search(rf"{re.escape(selector)}\s*\{{(?P<body>.*?)\}}", css, re.DOTALL)
    assert match is not None, f"Missing CSS block for {selector}"
    return match.group("body")


def test_collapsible_copy_button_mounts_and_copies_text() -> None:
    copied: list[str] = []

    class TestApp(App):
        def compose(self) -> ComposeResult:
            yield make_collapsible_with_copy_button(
                content=Vertical(Static("shell output", markup=False)),
                title="Shell #1",
                copy_handler=copied.append,
            )

    async def run_app() -> None:
        app = TestApp()
        async with app.run_test() as pilot:
            assert len(app.query(Button)) == 1
            await pilot.click(Button)
            assert copied == ["shell output"]

    asyncio.run(run_app())


def test_tools_result_widget_accepts_non_ascii_tool_names() -> None:
    collection = ToolResultCollection()
    collection.add("工具名称", 0.1, {"参数名称": "参数值"}, "执行结果")

    class TestApp(App):
        def compose(self) -> ComposeResult:
            yield ToolsResultWidget(collection)

    async def run_app() -> None:
        app = TestApp()
        async with app.run_test():
            assert len(app.query(Collapsible)) == 1

    asyncio.run(run_app())


def test_repl_input_button_labels_match_actions(monkeypatch) -> None:
    class FakeAgentManager:
        current_agent_name = "default"

        def agent_names(self) -> list[str]:
            return ["default"]

        def switch_agent(self, agent_name: str) -> bool:
            self.current_agent_name = agent_name
            return False

    class FakeWorkspace:
        root_path = Path(".")

    class FakeToolRegistry:
        pass

    class FakeResultManager:
        console = None

    monkeypatch.setattr("src.console.ui.repl.AgentManager", FakeAgentManager)
    monkeypatch.setattr(REPL, "on_mount", lambda self: None)

    async def run_app() -> None:
        app = REPL(FakeWorkspace(), FakeToolRegistry(), FakeResultManager())
        async with app.run_test():
            assert str(app.query_one("#submit-btn", Button).label) == "提交"
            assert str(app.query_one("#big-paste-btn", Button).label) == "大文本粘贴"
            assert str(app.query_one("#paste-submit-btn", Button).label) == "粘贴并提交"

    asyncio.run(run_app())


def test_input_buttons_fit_three_visible_rows() -> None:
    input_area = _css_block(REPL.CSS, "#input-area")
    assert "max-height: 12;" in input_area

    button_area = _css_block(REPL.CSS, "#button-area")
    assert "padding: 0 1;" in button_area

    expected_widths = {
        "#submit-btn": "width: 8;",
        "#big-paste-btn": "width: 14;",
        "#paste-submit-btn": "width: 16;",
    }
    for selector, width_rule in expected_widths.items():
        block = _css_block(REPL.CSS, selector)
        assert width_rule in block
        assert re.search(r"(?m)^\s*height:\s*3;", block) is not None
