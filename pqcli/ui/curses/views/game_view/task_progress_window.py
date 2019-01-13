import typing as T

from pqcli.mechanic import Player
from pqcli.ui.curses.widgets import (
    Focusable,
    Label,
    ProgressBar,
    WindowWrapper,
)


class TaskProgressWindow(Focusable, WindowWrapper):
    def __init__(
        self, player: Player, parent: T.Any, h: int, w: int, y: int, x: int
    ) -> None:
        super().__init__(parent, h, w, y, x)

        self._desc_win = Label(self._win, 1, w, 0, 0)
        self._progress_bar = ProgressBar(
            self._win, 1, w, 1, 0, show_time=False
        )

        self._player = player
        self._player.connect("new_task", self._sync_task_name)
        self._player.task_bar.connect("change", self._sync_position)

        self.sync()

    def stop(self) -> None:
        super().stop()

        self._desc_win.stop()
        self._progress_bar.stop()

        self._player.disconnect("new_task", self._sync_task_name)
        self._player.task_bar.disconnect("change", self._sync_position)

    def sync(self) -> None:
        self._sync_task_name()
        self._sync_position()

    def _sync_task_name(self) -> None:
        self._desc_win.set_text(
            f"{self._player.task.description}..." if self._player.task else "?"
        )

    def _sync_position(self) -> None:
        self._progress_bar.set_position(
            self._player.task_bar.position, self._player.task_bar.max_
        )
