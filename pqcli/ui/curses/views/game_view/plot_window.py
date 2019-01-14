import typing as T

from pqcli.lingo import act_name
from pqcli.mechanic import Player
from pqcli.ui.curses.widgets import Focusable, ListBox, WindowWrapper

from .progress_bar_window import ListBoxProgressBarWindow


class PlotWindow(Focusable, ListBoxProgressBarWindow):
    cutoff = 100

    def __init__(
        self, player: Player, parent: T.Any, h: int, w: int, y: int, x: int
    ) -> None:
        super().__init__(
            parent, h, w, y, x, " Plot Development ", show_time=True
        )
        self._on_focus_change += self._render

        self._player = player
        self._player.quest_book.connect("start_act", self._sync_act_add)
        self._player.quest_book.plot_bar.connect("change", self._sync_position)

        self.sync()

    def stop(self) -> None:
        super().stop()
        self._list_box.stop()

        self._player.quest_book.disconnect("start_act", self._sync_act_add)
        self._player.quest_book.plot_bar.disconnect(
            "change", self._sync_position
        )

    def scroll_page_up(self) -> None:
        self._list_box.scroll_page_up()
        self._render()

    def scroll_page_down(self) -> None:
        self._list_box.scroll_page_down()
        self._render()

    def sync(self) -> None:
        self._sync_acts()
        self._sync_position()

    def _sync_acts(self) -> None:
        self._list_box.clear()
        for act_number in range(
            max(0, self._player.quest_book.act - self.cutoff),
            self._player.quest_book.act + 1,
        ):
            self._sync_act_add(act_number)
        self._render_list_box()

    def _sync_act_add(self, act_number: int) -> None:
        self._list_box.delete(0, max(0, len(self._list_box) - self.cutoff))
        prev = self._list_box.get(-1)
        if prev is not None:
            self._list_box.set(-1, "[X] " + prev[4:])
        self._list_box.add("[ ] " + act_name(act_number))
        self._list_box.select(-1)
        self._render_list_box()

    def _sync_position(self) -> None:
        self._cur_pos = self._player.quest_book.plot_bar.position
        self._max_pos = self._player.quest_book.plot_bar.max_
        self._render_progress_bar()
