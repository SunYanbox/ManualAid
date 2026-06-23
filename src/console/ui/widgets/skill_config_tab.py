from __future__ import annotations

from typing import ClassVar

from textual.containers import Horizontal, Vertical
from textual.widgets import Button, DataTable, Label, Static


class SkillConfigTab(Vertical):
    """Skill 配置标签页.

    显示所有发现的 Skill,支持:
    - 查看全局和项目级 Skill
    - 启用/禁用 Skill
    - 查看 Skill 详情
    """

    DEFAULT_CSS: ClassVar[str] = """
    SkillConfigTab {
        height: 1fr;
        width: 1fr;
        padding: 0 1;
        overflow-y: auto;
    }

    #skill-header {
        height: auto;
        padding: 1 0;
        text-style: bold;
        color: $text;
        border-bottom: solid $primary;
    }

    #skill-toolbar {
        height: auto;
        padding: 1 0;
        align: left middle;
    }

    #skill-toolbar Button {
        margin-right: 1;
    }

    #skill-table {
        height: 1fr;
    }

    #skill-detail {
        height: auto;
        max-height: 10;
        padding: 1;
        margin-top: 1;
        background: $surface;
        border: solid $primary;
        overflow-y: auto;
    }

    #skill-empty {
        height: 100%;
        content-align: center middle;
        color: $text-muted;
    }

    .skill-row-enabled {
        color: $text;
    }

    .skill-row-disabled {
        color: $text-muted;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._skill_manager = None
        self._workspace_root = None
        self._skills_data: dict = {}
        self._columns_initialized = False  # 标记列是否已初始化

    def compose(self):
        yield Label("Skill 配置", id="skill-header")
        with Horizontal(id="skill-toolbar"):
            yield Button("刷新", id="skill-refresh-btn", variant="default")
            yield Button("启用选中", id="skill-enable-btn", variant="success")
            yield Button("禁用选中", id="skill-disable-btn", variant="warning")
            yield Button("启用全部", id="skill-enable-all-btn", variant="success")
            yield Button("禁用全部", id="skill-disable-all-btn", variant="warning")
        yield DataTable(id="skill-table")
        yield Static("选择 Skill 查看详情", id="skill-detail")

    def set_managers(self, skill_manager, workspace_root) -> None:
        """设置 Skill 管理器和工作区根目录."""
        self._skill_manager = skill_manager
        self._workspace_root = workspace_root
        # 发现 skills
        if workspace_root:
            from pathlib import Path

            skill_manager.discover(Path(workspace_root))
        self._refresh()

    def on_mount(self) -> None:
        table = self.query_one("#skill-table", DataTable)
        table.add_columns("启用", "名称", "类型", "描述")
        table.cursor_type = "row"
        self._columns_initialized = True
        # 如果已经有数据,刷新显示
        if self._skills_data:
            self._refresh()

    def _refresh(self) -> None:
        """刷新 Skill 列表."""
        if self._skill_manager is None:
            return

        # 重新获取所有技能(会从数据库加载禁用状态)
        self._skills_data = self._skill_manager.get_all()

        # 如果列还没初始化,不刷新(等 on_mount 后自动刷新)
        if not self._columns_initialized:
            return

        table = self.query_one("#skill-table", DataTable)
        table.clear()

        # 获取当前禁用状态用于显示
        disabled_set = self._skill_manager.get_disabled()

        for name, skill in self._skills_data.items():
            is_global = skill.metadata.get("is_global", True)
            skill_type = "全局" if is_global else "项目"
            # 使用禁用集合判断状态,确保与持久化数据一致
            is_enabled = name not in disabled_set
            status = "✓" if is_enabled else "✗"
            description = skill.description[:50] + "..." if len(skill.description) > 50 else skill.description
            table.add_row(status, name, skill_type, description)

    def _update_detail(self, row_index: int) -> None:
        """更新详情显示."""
        if self._skill_manager is None:
            return

        table = self.query_one("#skill-table", DataTable)
        if row_index is None or row_index < 0:
            return

        row_data = table.get_row_at(row_index)
        if not row_data:
            return

        name = row_data[1]
        skill = self._skills_data.get(name)
        if not skill:
            return

        detail_text = f"[bold]{skill.name}[/bold]\n位置: {skill.location}\n类型: {'全局' if skill.metadata.get('is_global', True) else '项目'}\n状态: {'启用' if skill.enabled else '禁用'}\n\n描述: {skill.description}"

        detail = self.query_one("#skill-detail", Static)
        detail.update(detail_text)

    async def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """行高亮时更新详情."""
        if event.data_table.id == "skill-table":
            self._update_detail(event.cursor_row)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if self._skill_manager is None:
            return

        button_id = event.button.id or ""

        if button_id == "skill-refresh-btn":
            if self._workspace_root:
                from pathlib import Path

                self._skill_manager.discover(Path(self._workspace_root))
            self._refresh()
            self.notify("已刷新 Skill 列表")

        elif button_id == "skill-enable-btn":
            # 启用选中的 Skill
            table = self.query_one("#skill-table", DataTable)
            row_index = table.cursor_row
            if row_index is None or row_index < 0:
                self.notify("请先选择一个 Skill", severity="warning")
                return

            row_data = table.get_row_at(row_index)
            if not row_data:
                return

            name = row_data[1]
            disabled = self._skill_manager.get_disabled()
            if name in disabled:
                disabled.discard(name)
                self._skill_manager.set_disabled(disabled, persist=True)
                self._refresh()
                self.notify(f"已启用: {name}")
            else:
                self.notify(f"{name} 已经是启用状态", severity="information")

        elif button_id == "skill-disable-btn":
            # 禁用选中的 Skill
            table = self.query_one("#skill-table", DataTable)
            row_index = table.cursor_row
            if row_index is None or row_index < 0:
                self.notify("请先选择一个 Skill", severity="warning")
                return

            row_data = table.get_row_at(row_index)
            if not row_data:
                return

            name = row_data[1]
            disabled = self._skill_manager.get_disabled()
            if name not in disabled:
                disabled.add(name)
                self._skill_manager.set_disabled(disabled, persist=True)
                self._refresh()
                self.notify(f"已禁用: {name}")
            else:
                self.notify(f"{name} 已经是禁用状态", severity="information")

        elif button_id == "skill-enable-all-btn":
            self._skill_manager.set_disabled(set(), persist=True)
            self._refresh()
            self.notify("已启用所有 Skill")

        elif button_id == "skill-disable-all-btn":
            all_names = set(self._skills_data.keys())
            self._skill_manager.set_disabled(all_names, persist=True)
            self._refresh()
            self.notify("已禁用所有 Skill")

    async def on_data_table_cell_selected(self, event: DataTable.CellSelected) -> None:
        """单元格选中时切换启用状态(点击启用列)."""
        if event.data_table.id != "skill-table":
            return

        if event.column_key != 0:  # 只在"启用"列点击时切换
            return

        if self._skill_manager is None:
            return

        row_data = event.data_table.get_row_at(event.cursor_row)
        if not row_data:
            return

        name = row_data[1]
        skill = self._skills_data.get(name)
        if not skill:
            return

        # 切换状态
        disabled = self._skill_manager.get_disabled()
        if name in disabled:
            disabled.discard(name)
        else:
            disabled.add(name)

        self._skill_manager.set_disabled(disabled, persist=True)
        self._refresh()

        status = "启用" if name not in disabled else "禁用"
        self.notify(f"已{status}: {name}")
