"""Statistics tab — session stats, tool ranking, session management."""

from __future__ import annotations

from typing import ClassVar

from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Input, Label, Static


class RenameDialog(ModalScreen[str | None]):
    """Modal dialog for renaming a session."""

    DEFAULT_CSS = """
    RenameDialog {
        align: center middle;
    }

    #rename-dialog {
        width: 40;
        height: auto;
        padding: 2;
        border: thick $primary;
        background: $surface;
    }

    #rename-dialog > Label {
        text-style: bold;
        margin-bottom: 1;
    }

    #rename-input {
        margin-bottom: 1;
    }

    #rename-buttons {
        height: auto;
        align: right middle;
    }

    #rename-buttons Button {
        margin-left: 1;
    }
    """

    def __init__(self, session_id: int, current_name: str) -> None:
        super().__init__()
        self._session_id = session_id
        self._current_name = current_name

    def compose(self):
        with Vertical(id="rename-dialog"):
            yield Label("Rename Session")
            yield Input(value=self._current_name, id="rename-input")
            with Horizontal(id="rename-buttons"):
                yield Button("Cancel", id="cancel-btn", variant="default")
                yield Button("OK", id="ok-btn", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "ok-btn":
            new_name = self.query_one("#rename-input", Input).value
            self.dismiss(new_name)
        elif event.button.id == "cancel-btn":
            self.dismiss(None)


class QuestionDialog(ModalScreen[bool]):
    """Simple yes/no confirmation dialog."""

    DEFAULT_CSS = """
    QuestionDialog {
        align: center middle;
    }

    #question-dialog {
        width: 50;
        height: auto;
        padding: 2;
        border: thick $primary;
        background: $surface;
    }

    #question-dialog > Label {
        text-style: bold;
        margin-bottom: 1;
    }

    #question-message {
        margin-bottom: 1;
    }

    #question-buttons {
        height: auto;
        align: right middle;
    }

    #question-buttons Button {
        margin-left: 1;
    }
    """

    def __init__(self, title: str, message: str) -> None:
        super().__init__()
        self._title = title
        self._message = message

    def compose(self):
        with Vertical(id="question-dialog"):
            yield Label(self._title)
            yield Label(self._message, id="question-message")
            with Horizontal(id="question-buttons"):
                yield Button("Cancel", id="cancel-btn", variant="default")
                yield Button("OK", id="ok-btn", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "ok-btn":
            self.dismiss(True)
        elif event.button.id == "cancel-btn":
            self.dismiss(False)


class StatsTab(Vertical):
    """Statistics & session management tab.

    Displays:
    - Overview (total sessions, calls, success rate)
    - Current session stats (DataTable)
    - Tool usage ranking (DataTable, top 10)
    - Session list with rename/delete buttons.
    """

    DEFAULT_CSS: ClassVar[str] = """
    StatsTab {
        height: 1fr;
        width: 1fr;
        padding: 0 1;
        overflow-y: auto;
    }

    #stats-placeholder {
        height: 100%;
        content-align: center middle;
        color: $text-muted;
    }

    #stats-empty {
        height: 100%;
        content-align: center middle;
        color: $text-muted;
    }

    .stats-header {
        height: auto;
        padding: 1 0;
        text-style: bold;
        color: $text;
        border-bottom: solid $primary;
    }

    #stats-overview {
        height: auto;
        padding: 1;
        background: $surface;
        border: solid $primary;
        margin-bottom: 1;
    }

    StatsTab DataTable {
        height: auto;
        max-height: 12;
        margin-bottom: 1;
    }

    .stats-session-row {
        height: auto;
        padding: 0 0;
        margin-bottom: 0;
        align: left middle;
    }

    .stats-session-name {
        width: 1fr;
        height: auto;
        padding: 0 1;
    }

    .stats-session-row Button {
        margin-left: 1;
    }

    #stats-pagination {
        height: auto;
        padding: 0 0;
        margin-bottom: 1;
        align: center middle;
    }

    #stats-pagination Label {
        margin: 0 1;
    }

    #stats-pagination Button {
        margin: 0 0;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._db = None
        self._current_session_id: int | None = None
        self._session_page: int = 0
        self._sessions_per_page: int = 15

    def compose(self):
        yield Label("Loading statistics...", id="stats-placeholder")

    def set_database(self, db, current_session_id: int | None) -> None:
        """Set database reference and refresh."""
        self._db = db
        self._current_session_id = current_session_id
        self.set_timer(0.0, self._refresh)

    def on_mount(self) -> None:
        if self._db is not None:
            self.set_timer(0.1, self._refresh)
        self.set_interval(1.0, self._update_live_duration)

    def _update_live_duration(self) -> None:
        """Update current session duration display every second."""
        if self._db is None or self._current_session_id is None:
            return
        try:
            dt = self.query_one("#stats-current-session", DataTable)
        except Exception:
            return

        row = self._db.fetchone(
            "SELECT created_at FROM sessions WHERE id = ?",
            (self._current_session_id,),
        )
        if not row:
            return

        import time

        duration = time.time() - row[0]
        duration_str = self._format_duration(duration)
        dt.update_cell_at((0, 1), duration_str)

    def _format_duration(self, seconds: float) -> str:
        """Format seconds to human-readable string."""
        if seconds < 60:
            return f"{seconds:.0f}s"
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        if minutes < 60:
            return f"{minutes}m {secs}s"
        hours = minutes // 60
        minutes = minutes % 60
        return f"{hours}h {minutes}m {secs}s"

    async def _refresh(self) -> None:
        """Rebuild the entire stats UI."""
        if self._db is None:
            return

        await self.remove_children()
        self._build_content()

    def _build_content(self) -> None:
        """Mount all content widgets."""
        if self._db is None:
            return

        sessions = self._db.get_all_sessions()
        total_sessions = len(sessions)

        # Compute global aggregates
        total_calls = 0
        total_success = 0
        for s in sessions:
            sid = s[0]
            summary = self._db.get_session_summary(sid)
            total_calls += summary["total_calls"]
            total_success += summary["success_count"]

        success_rate = (total_success / total_calls * 100) if total_calls else 0.0

        # Current session name
        current_name = ""
        if self._current_session_id is not None:
            row = self._db.fetchone(
                "SELECT name FROM sessions WHERE id = ?",
                (self._current_session_id,),
            )
            if row:
                current_name = row[0]

        # --- Section 1: Overview ---
        overview_text = (
            f"[bold]Overview[/bold]\n"
            f"Total Sessions: {total_sessions}\n"
            f"Total Tool Calls: {total_calls}\n"
            f"Overall Success Rate: {success_rate:.1f}%\n"
            f"Active Session: {current_name or 'N/A'}"
        )
        self.mount(Static(overview_text, id="stats-overview"))

        # --- Section 2: Current session stats ---
        if self._current_session_id is not None:
            summary = self._db.get_session_summary(self._current_session_id)
            if summary:
                duration_str = self._format_duration(summary["duration"])
                self.mount(Label("Current Session", classes="stats-header"))
                dt = DataTable(id="stats-current-session")
                dt.add_columns("Metric", "Value")
                dt.add_row("Duration", duration_str)
                dt.add_row("Total Calls", str(summary["total_calls"]))
                dt.add_row("Successful", str(summary["success_count"]))
                dt.add_row("Failed", str(summary["fail_count"]))
                dt.add_row("Success Rate", f"{summary['success_rate']:.1f}%")
                self.mount(dt)

        # --- Section 3: Tool usage ranking ---
        ranking = self._db.get_tool_usage_ranking(self._current_session_id)
        if ranking:
            self.mount(Label("Top Tools", classes="stats-header"))
            dt = DataTable(id="stats-tool-ranking")
            dt.add_columns("#", "Tool", "Calls", "Avg Time", "Total Time")
            for i, (func_name, count, avg_dur, total_dur) in enumerate(ranking, 1):
                avg_str = f"{avg_dur:.1f}ms" if avg_dur is not None else "N/A"
                total_str = f"{total_dur:.1f}ms" if total_dur is not None else "N/A"
                dt.add_row(str(i), func_name, str(count), avg_str, total_str)
            self.mount(dt)
        else:
            self.mount(Label("No tool calls recorded yet.", id="stats-empty"))

        # --- Section 4: Session list ---
        if sessions:
            total_pages = (len(sessions) + self._sessions_per_page - 1) // self._sessions_per_page
            if self._session_page >= total_pages:
                self._session_page = total_pages - 1
            if self._session_page < 0:
                self._session_page = 0

            start_idx = self._session_page * self._sessions_per_page
            end_idx = start_idx + self._sessions_per_page
            page_sessions = sessions[start_idx:end_idx]

            self.mount(Label("Sessions", classes="stats-header"))

            if total_pages > 1:
                nav = Horizontal(
                    Button("<< Prev", id="page-prev", variant="default", disabled=(self._session_page == 0)),
                    Label(f" Page {self._session_page + 1}/{total_pages} "),
                    Button(
                        "Next >>", id="page-next", variant="default", disabled=(self._session_page >= total_pages - 1)
                    ),
                    id="stats-pagination",
                    classes="stats-pagination",
                )
                self.mount(nav)

            for s in page_sessions:
                sid, name, _created_at, duration = s
                is_active = sid == self._current_session_id
                name_display = name or "Unnamed"
                if is_active:
                    name_display += "  (active)"

                duration_str = self._format_duration(duration) if duration else "in progress"

                # Get tool call count for this session
                summary = self._db.get_session_summary(sid)
                total_calls = summary.get("total_calls", 0) if summary else 0

                text = f"{name_display}  [{duration_str}]  ({total_calls} calls)"

                row = Horizontal(
                    Static(text, classes="stats-session-name"),
                    Button("Rename", id=f"rename-{sid}", variant="default"),
                    Button("Delete", id=f"delete-{sid}", variant="error"),
                    classes="stats-session-row",
                )
                self.mount(row)
                if is_active:
                    row.query_one(f"#delete-{sid}", Button).disabled = True

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle rename/delete button clicks."""
        if self._db is None:
            return

        button_id = event.button.id or ""

        # Pagination buttons
        if button_id == "page-prev":
            self._session_page -= 1
            await self._refresh()
            return
        elif button_id == "page-next":
            self._session_page += 1
            await self._refresh()
            return

        parts = button_id.split("-", 1)
        if len(parts) != 2:
            return

        action, sid_str = parts
        try:
            session_id = int(sid_str)
        except ValueError:
            return

        if action == "rename":
            # Get current name
            row = self._db.fetchone(
                "SELECT name FROM sessions WHERE id = ?",
                (session_id,),
            )
            current_name = row[0] if row else ""

            async def on_rename(result: str | None) -> None:
                if result is not None and result.strip():
                    self._db.rename_session(session_id, result.strip())
                    await self._refresh()
                elif result is not None:
                    self.notify("Name cannot be empty.", severity="warning")

            self.app.push_screen(RenameDialog(session_id, current_name), on_rename)

        elif action == "delete":
            if session_id == self._current_session_id:
                self.notify("Cannot delete the active session.", severity="error")
                return

            async def on_confirm(result: bool | None) -> None:
                if result:
                    self._db.delete_session_async(session_id)
                    self.notify(
                        f"Session '{session_id}' scheduled for deletion.",
                    )
                    await self._refresh()

            self.app.push_screen(
                QuestionDialog(
                    "Delete Session",
                    f"Are you sure you want to delete session '{session_id}'?\n"
                    "All tool calls and snapshots for this session will also be deleted.",
                ),
                on_confirm,
            )
