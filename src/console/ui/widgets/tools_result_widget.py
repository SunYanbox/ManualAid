"""Tools result widget for displaying tool execution results"""

from __future__ import annotations

from typing import ClassVar

from textual.containers import Vertical
from textual.widgets import Collapsible, DataTable, Static

from src.models.tools.tool_result_collection import ToolResultCollection
from src.utils.string_snapshot import truncate_params_string


class ToolsResultWidget(Vertical):
    """Widget for displaying tool execution results.

    Contains:
    - A data table showing call count, total time, and average time per tool
    - Collapsible sections for each tool's results with parameter summary as title
    """

    DEFAULT_CSS: ClassVar[str] = """
    ToolsResultWidget {
        height: 40;
        width: 1fr;
        border: solid green;
        padding: 1;
    }

    #tools-result-table {
        height: 10;
        width: 1fr;
    }

    #tools-result-collapsibles {
        height: 1fr;
        overflow-y: auto;
    }
    """

    def __init__(self, collection: ToolResultCollection | None = None) -> None:
        super().__init__()
        self._collection: ToolResultCollection | None = collection

    def compose(self):
        yield DataTable(id="tools-result-table")
        yield Vertical(id="tools-result-collapsibles")

    def on_mount(self) -> None:
        """Called when the widget is mounted. Update display if collection is set."""
        if self._collection is not None:
            self._update_display()

    def set_collection(self, collection: ToolResultCollection | None) -> None:
        """Set the tool result collection and update the display.

        Args:
            collection: The ToolResultCollection to display.
        """
        self._collection = collection
        if self.is_mounted:
            self._update_display()

    def _update_display(self) -> None:
        """Update both table and collapsibles."""
        self._update_table()
        self._update_collapsibles()
        self.refresh()

    def _update_table(self) -> None:
        """Update the data table with tool statistics."""
        if self._collection is None:
            return

        try:
            table = self.query_one("#tools-result-table", DataTable)
        except Exception:
            return

        table.clear(columns=True)
        table.add_columns("Tool", "Calls", "Total Time (s)", "Avg Time (s)")

        for tool_name in self._collection.tools():
            times = self._collection.consumes.get(tool_name, [])
            call_count = len(times)
            total_time = sum(times)
            avg_time = self._collection.get_avg_consume(tool_name)

            table.add_row(
                tool_name,
                str(call_count),
                f"{total_time:.4f}",
                f"{avg_time:.4f}",
            )

    def _update_collapsibles(self) -> None:
        """Update the collapsible sections with tool results."""
        if self._collection is None:
            return

        try:
            container = self.query_one("#tools-result-collapsibles", Vertical)
        except Exception:
            return

        container.remove_children()

        for tool_name in self._collection.tools():
            results = self._collection.results.get(tool_name, [])
            for index, (kwargs, result) in enumerate(results):
                # Create title with tool name and parameter summary
                params_str = ", ".join(f"{k}={v}" for k, v in kwargs.items()) if kwargs else "no parameters"
                truncated_params = truncate_params_string(params_str)
                title = f"[bold cyan]{tool_name}[/bold cyan] | [dim]{truncated_params}[/dim]"

                # Create content widget
                content_widget = Static(result, id=f"result-{tool_name}-{index}")

                # Create collapsible
                collapsible = Collapsible(
                    content_widget,
                    title=title,
                    id=f"collapsible-{tool_name}-{index}",
                )
                container.mount(collapsible)
