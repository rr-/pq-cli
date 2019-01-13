import curses
import datetime
import typing as T

from pqcli.lingo import format_timespan
from pqcli.ui.curses.colors import COLOR_PROGRESSBAR, has_colors
from pqcli.ui.curses.widgets.base import WindowWrapper


class ProgressBar(WindowWrapper):
    def __init__(
        self, parent: T.Any, h: int, w: int, y: int, x: int, show_time: bool
    ) -> None:
        super().__init__(parent, h, w, y, x)

        self._cur_pos = 0.0
        self._max_pos = 1.0

        self._show_time = show_time
        self._last_tick: T.Optional[T.Tuple[datetime.datetime, float]] = None

    @property
    def time_left(self) -> T.Optional[datetime.timedelta]:
        if self._last_tick is None:
            return None
        time_then, pos_then = self._last_tick
        time_now, pos_now = datetime.datetime.now(), self._cur_pos
        speed = (pos_now - pos_then) / (time_now - time_then).total_seconds()
        if not speed:
            return None
        return datetime.timedelta(seconds=(self._max_pos - pos_now) / speed)

    def set_position(self, cur_pos: float, max_pos: float) -> None:
        if not self._win:
            return
        self._win.erase()

        if self._last_tick is None or cur_pos == 0 or max_pos != self._max_pos:
            self._last_tick = (datetime.datetime.now(), cur_pos)
        self._cur_pos = cur_pos
        self._max_pos = max_pos

        text = f"{cur_pos / max_pos:.02%}"
        if self.time_left and self._show_time:
            text += f" ({format_timespan(self.time_left)})"

        x = max(0, (self.getmaxyx()[1] - len(text)) // 2)
        self._win.addnstr(0, x, text, min(len(text), self.getmaxyx()[1] - 1))
        x = int(cur_pos * self.getmaxyx()[1] // max_pos)
        if x > 0:
            self._win.chgat(
                0,
                0,
                curses.color_pair(COLOR_PROGRESSBAR)
                if has_colors()
                else curses.A_REVERSE,
            )
            if x < self.getmaxyx()[1]:
                self._win.chgat(0, x, curses.A_NORMAL)
        self._win.noutrefresh()
