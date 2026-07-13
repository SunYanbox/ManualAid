"""Helper for creating collapsible items with button rows."""

from __future__ import annotations

from collections.abc import Callable

from textual.containers import Horizontal, Vertical
from textual.widget import Widget
from textual.widgets import Button, Collapsible, Static


class CollapsibleCopyContent(Vertical):
    """Content container that handles its own copy button."""

    def __init__(
        self,
        content: Vertical,
        on_copy: Callable[[str], None],
        copy_button_text: str,
    ) -> None:
        super().__init__()
        self._content = content
        self._on_copy = on_copy
        self._copy_button_text = copy_button_text

    def compose(self):
        yield self._content
        yield Horizontal(Button(self._copy_button_text, variant="default", classes="copy-output-btn"))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if not event.button.has_class("copy-output-btn"):
            return

        output_text = _static_text(self._content)
        if output_text:
            self._on_copy(output_text)
        event.stop()


def _static_text(widget: Widget) -> str:
    for child in widget.children:
        if isinstance(child, Static) and not child.id:
            return str(child.render())
        text = _static_text(child)
        if text:
            return text
    return ""


def make_collapsible_item(
    content: Vertical,
    title: str,
    collapsed: bool = False,
    on_copy: Callable[[str], None] | None = None,
    copy_button_text: str = "复制输出",
) -> Collapsible:
    """Create a collapsible item with optional copy button.

    Args:
        content: Vertical container with the content
        title: Title for the collapsible
        collapsed: Whether the item is collapsed by default
        on_copy: Callback when copy button is clicked
        copy_button_text: Text for the copy button

    Returns:
        Collapsible widget
    """
    if on_copy:
        content = CollapsibleCopyContent(content, on_copy, copy_button_text)

    return Collapsible(content, title=title, collapsed=collapsed)


def make_collapsible_with_copy_button(
    content: Vertical,
    title: str,
    copy_handler: Callable[[str], None],
    collapsed: bool = False,
) -> Collapsible:
    """Create a collapsible item with copy button (convenience wrapper).

    Args:
        content: Vertical container with the content
        title: Title for the collapsible
        copy_handler: Function to call when copy button is clicked
        collapsed: Whether the item is collapsed by default

    Returns:
        Collapsible widget with copy button
    """
    return make_collapsible_item(
        content=content,
        title=title,
        collapsed=collapsed,
        on_copy=copy_handler,
    )
