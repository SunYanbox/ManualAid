"""Base modal dialog for Textual UI."""

from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label


class ModalDialog[T](ModalScreen[T]):
    """Base modal dialog with consistent structure.

    Usage:
        class MyDialog(ModalDialog[str]):
            def compose(self):
                yield Label("My title")
                yield Input(id="my-input")

            def on_button_pressed(self, event: Button.Pressed) -> None:
                if event.button.id == "ok-btn":
                    value = self.query_one("#my-input", Input).value
                    self.dismiss(value)
                elif event.button.id == "cancel-btn":
                    self.dismiss(None)

        # Show dialog
        app.push_screen(MyDialog(), callback)
    """

    DEFAULT_CSS = """
    ModalDialog {
        align: center middle;
    }

    #modal-container {
        width: 40;
        height: auto;
        padding: 2;
        border: thick $primary;
        background: $surface;
    }

    #modal-container > Label {
        text-style: bold;
        margin-bottom: 1;
    }

    #modal-container > Input {
        margin-bottom: 1;
    }

    #modal-buttons {
        height: auto;
        align: right middle;
    }

    #modal-buttons Button {
        margin-left: 1;
    }
    """

    def compose(self) -> None:
        """Override this method to define dialog content."""
        raise NotImplementedError


class RenameDialog(ModalDialog[str | None]):
    """Modal dialog for renaming a session."""

    def __init__(self, session_id: int, current_name: str) -> None:
        super().__init__()
        self._session_id = session_id
        self._current_name = current_name

    def compose(self) -> None:
        with Vertical(id="modal-container"):
            yield Label("重命名会话")
            yield Input(value=self._current_name, id="rename-input")
            with Horizontal(id="modal-buttons"):
                yield Button("取消", id="cancel-btn", variant="default")
                yield Button("确定", id="ok-btn", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "ok-btn":
            new_name = self.query_one("#rename-input", Input).value
            self.dismiss(new_name)
        elif event.button.id == "cancel-btn":
            self.dismiss(None)


class QuestionDialog(ModalDialog[bool]):
    """Simple yes/no confirmation dialog."""

    def __init__(self, title: str, message: str) -> None:
        super().__init__()
        self._title = title
        self._message = message

    def compose(self) -> None:
        with Vertical(id="modal-container"):
            yield Label(self._title)
            yield Label(self._message, id="question-message")
            with Horizontal(id="modal-buttons"):
                yield Button("取消", id="cancel-btn", variant="default")
                yield Button("确定", id="ok-btn", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "ok-btn":
            self.dismiss(True)
        elif event.button.id == "cancel-btn":
            self.dismiss(False)


class EnvEditDialog(ModalDialog[dict | None]):
    """Dialog for editing environment variables."""

    def __init__(self, vars: dict) -> None:
        super().__init__()
        self._vars = vars

    def compose(self) -> None:
        with Vertical(id="modal-container"):
            yield Label("编辑环境变量")
            for name, value in self._vars.items():
                yield Input(value=value, id=f"env-{name}", name=name)
            with Horizontal(id="modal-buttons"):
                yield Button("取消", id="cancel-btn", variant="default")
                yield Button("确定", id="ok-btn", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "ok-btn":
            env_vars = {}
            for name in self._vars:
                env_input = self.query_one(f"#env-{name}", Input)
                if env_input.value:
                    env_vars[name] = env_input.value
            self.dismiss(env_vars)
        elif event.button.id == "cancel-btn":
            self.dismiss(None)
