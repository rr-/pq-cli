import curses
import typing as T

from pqcli.lingo import to_roman
from pqcli.mechanic import InventoryItem, Player
from pqcli.ui.curses.widgets import (
    DataTable,
    Focusable,
    ProgressBar,
    WindowWrapper,
)

from .progress_bar_window import DataTableProgressBarWindow


class InventoryWindow(Focusable, DataTableProgressBarWindow):
    def __init__(
        self, player: Player, parent: T.Any, h: int, w: int, y: int, x: int
    ) -> None:
        super().__init__(
            parent,
            h,
            w,
            y,
            x,
            " Inventory ",
            align_right=True,
            show_time=False,
        )
        self._on_focus_change += self._render

        self._player = player
        self._player.connect("new_task", self._on_new_task)
        self._player.inventory.connect("gold_change", self._sync_gold)
        self._player.inventory.connect("item_add", self._sync_item_add)
        self._player.inventory.connect("item_del", self._sync_item_del)
        self._player.inventory.connect("item_change", self._sync_item_change)
        self._player.inventory.encum_bar.connect(
            "change", self._sync_encumbrance
        )

        self.sync()

    def stop(self) -> None:
        super().stop()

        self._player.disconnect("new_task", self._on_new_task)
        self._player.inventory.disconnect("gold_change", self._sync_gold)
        self._player.inventory.disconnect("item_add", self._sync_item_add)
        self._player.inventory.disconnect("item_del", self._sync_item_del)
        self._player.inventory.disconnect(
            "item_change", self._sync_item_change
        )
        self._player.inventory.encum_bar.disconnect(
            "change", self._sync_encumbrance
        )

    def scroll_page_up(self) -> None:
        self._data_table.scroll_page_up()
        self._render()

    def scroll_page_down(self) -> None:
        self._data_table.scroll_page_down()
        self._render()

    def sync(self) -> None:
        self._sync_gold()
        self._sync_items()
        self._sync_encumbrance()

    def _sync_encumbrance(self) -> None:
        self._cur_pos = self._player.inventory.encum_bar.position
        self._max_pos = self._player.inventory.encum_bar.max_
        self._progress_title = (
            f"Encumbrance ({self._cur_pos:.0f}/{self._max_pos} cubits)"
        )
        self._render_progress_bar()

    def _sync_gold(self) -> None:
        self._data_table.set("Gold", str(self._player.inventory.gold))
        self._data_table.select("Gold")
        self._render_data_table()

    def _sync_items(self) -> None:
        self._data_table.clear()
        self._sync_gold()
        for item in self._player.inventory:
            self._data_table.add(item.name, str(item.quantity))
        self._data_table.scroll_to_item(0)
        self._data_table.select(None)
        self._render_data_table()

    def _sync_item_add(self, item: InventoryItem) -> None:
        self._data_table.add(item.name, str(item.quantity))
        self._data_table.select(item.name)
        self._render_data_table()

    def _sync_item_del(self, item: InventoryItem) -> None:
        self._data_table.delete(item.name)
        self._data_table.select(None)
        self._render_data_table()

    def _sync_item_change(self, item: InventoryItem) -> None:
        self._data_table.set(item.name, str(item.quantity))
        self._data_table.select(item.name)
        self._render_data_table()

    def _on_new_task(self) -> None:
        description = (
            self._player.task.description if self._player.task else "?"
        )
        if description.lower().startswith("sell"):
            self._data_table.scroll_to_item(0)
