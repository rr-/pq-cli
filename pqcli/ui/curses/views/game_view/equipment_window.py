import typing as T

from pqcli.mechanic import EquipmentType, Player
from pqcli.ui.curses.widgets import DataTable, Focusable, WindowWrapper


class EquipmentWindow(Focusable, WindowWrapper):
    def __init__(
        self, player: Player, parent: T.Any, h: int, w: int, y: int, x: int
    ) -> None:
        super().__init__(parent, h, w, y, x)
        self._on_focus_change += self._render

        self._data_table = DataTable(
            self._win, h - 2, w - 2, 1, 1, align_right=False
        )

        self._player = player
        self._player.equipment.connect("change", self._sync_equipment_change)

        self.sync()

    def stop(self) -> None:
        super().stop()
        self._data_table.stop()

        self._player.equipment.disconnect(
            "change", self._sync_equipment_change
        )

    def sync(self) -> None:
        self._data_table.clear()
        for equipment_type in EquipmentType:
            self._data_table.add(
                equipment_type.value.ljust(15),
                self._player.equipment[equipment_type] or "",
            )
        self._data_table.select(None)
        self._render()

    def _sync_equipment_change(
        self, equipment_type: EquipmentType, item_name: T.Optional[str]
    ) -> None:
        self._data_table.set(equipment_type.value, item_name or "")
        self._data_table.select(equipment_type.value)
        self._render()

    def _render(self) -> None:
        if not self._win:
            return

        with self.focus_standout(self._win):
            self._win.box()
            text = " Equipment "
            x = max(0, (self.getmaxyx()[1] - len(text)) // 2)
            self._win.addnstr(0, x, text, min(len(text), self.getmaxyx()[1]))

        self._win.noutrefresh()
        self._data_table.render()
