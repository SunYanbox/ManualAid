"""Mixin for tabs that need to refresh display."""

from __future__ import annotations

from textual.containers import Vertical


class RefreshableTab(Vertical):
    """Mixin for tabs that need to rebuild their content.

    Provides a common pattern to remove existing children and call
    _build_content() to mount new content.
    """

    def _refresh(self) -> None:
        """Refresh the tab content."""
        # Override in subclass
        pass

    def _build_content(self) -> None:
        """Build the tab content. Override this method."""
        raise NotImplementedError
