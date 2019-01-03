import curses

from .base import WindowWrapper


class ProgressBar(WindowWrapper):
    def set_position(self, position: float, max_: float) -> None:
        if not self._win:
            return
        self._win.erase()
        text = f"{position / max_:.02%}"
        x = max(0, (self.getmaxyx()[1] - len(text)) // 2)
        self._win.addnstr(0, x, text, min(len(text), self.getmaxyx()[1] - 1))
        x = int(position * self.getmaxyx()[1] // max_)
        if x > 0:
            self._win.chgat(0, 0, curses.A_REVERSE)
            if x < self.getmaxyx()[1]:
                self._win.chgat(0, x, curses.A_NORMAL)
        self._win.noutrefresh()
