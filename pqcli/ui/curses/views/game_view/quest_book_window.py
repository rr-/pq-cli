import typing as T

from pqcli.mechanic import Player
from pqcli.ui.curses.widgets import ListBox, WindowWrapper

from .progress_bar_window import ListBoxProgressBarWindow


class QuestBookWindow(ListBoxProgressBarWindow):
    cutoff = 100

    def __init__(
        self, player: Player, parent: T.Any, h: int, w: int, y: int, x: int
    ) -> None:
        super().__init__(parent, h, w, y, x, " Quests ")

        self._player = player
        self._player.quest_book.connect("start_quest", self._sync_quest_add)
        self._player.quest_book.quest_bar.connect(
            "change", self._sync_position
        )

        self._sync()

    def stop(self) -> None:
        super().stop()
        self._list_box.stop()

        self._player.quest_book.disconnect("start_quest", self._sync_quest_add)
        self._player.quest_book.quest_bar.disconnect(
            "change", self._sync_position
        )

    def _sync(self) -> None:
        self._sync_quests()
        self._sync_position()

    def _sync_quests(self) -> None:
        self._list_box.clear()
        for quest_name in self._player.quest_book.quests[-self.cutoff :]:
            self._sync_quest_add(quest_name)
        self._render()

    def _sync_quest_add(self, quest_name: str) -> None:
        self._list_box.delete(0, max(0, len(self._list_box) - self.cutoff))
        prev = self._list_box.get(-1)
        if prev is not None:
            self._list_box.set(-1, "[X] " + prev[4:])
        self._list_box.add("[ ] " + quest_name)

    def _sync_position(self) -> None:
        self._render_progress_bar(
            self._player.quest_book.quest_bar.position,
            self._player.quest_book.quest_bar.max_,
            "",
        )

    def _render(self) -> None:
        if not self._win:
            return

        self._win.box()
        text = " Plot Development "
        x = max(0, (self.getmaxyx()[1] - len(text)) // 2)
        self._win.addnstr(0, x, text, min(len(text), self.getmaxyx()[1]))
        self._win.refresh()
        self._list_box.render()
