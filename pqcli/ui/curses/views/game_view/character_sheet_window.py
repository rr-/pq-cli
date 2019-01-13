import typing as T

from pqcli.mechanic import Player, StatType
from pqcli.ui.curses.widgets import Focusable

from .progress_bar_window import DataTableProgressBarWindow


class CharacterSheetWindow(Focusable, DataTableProgressBarWindow):
    def __init__(
        self, player: Player, parent: T.Any, h: int, w: int, y: int, x: int
    ) -> None:
        super().__init__(
            parent,
            h,
            w,
            y,
            x,
            " Character Sheet ",
            align_right=False,
            show_time=True,
        )
        self._on_focus_change += self._render

        self._focused = True

        self._player = player
        self._player.connect("level_up", self._sync_traits)
        self._player.stats.connect("change", self._sync_traits)
        self._player.exp_bar.connect("change", self._sync_exp)

        self.sync()

    def stop(self) -> None:
        super().stop()

        self._player.disconnect("level_up", self._sync_traits)
        self._player.stats.disconnect("change", self._sync_traits)
        self._player.exp_bar.disconnect("change", self._sync_exp)

    def sync(self) -> None:
        self._sync_traits()
        self._sync_exp()

    def _sync_traits(self) -> None:
        if not self._win:
            return

        self._data_table.clear()
        self._data_table.add("Name", self._player.name)
        self._data_table.add("Race", self._player.race.name)
        self._data_table.add("Class", self._player.class_.name)
        self._data_table.add("Level", str(self._player.level))
        self._data_table.add(" " * 15, "")
        for stat in StatType:
            self._data_table.add(stat.value, str(self._player.stats[stat]))

        self._render_data_table()

    def _sync_exp(self) -> None:
        self._cur_pos = self._player.exp_bar.position
        self._max_pos = self._player.exp_bar.max_
        self._progress_title = (
            f"Experience ({self._max_pos-self._cur_pos:.0f} XP to go)"
        )
        self._render_progress_bar()
