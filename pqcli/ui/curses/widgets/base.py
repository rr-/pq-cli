import curses
from typing import Any


class Widget:
    def __del__(self) -> None:
        self.stop()

    def stop(self) -> None:
        pass


class WindowWrapper(Widget):
    def __init__(
        self, parent: Any | None, h: int, w: int, y: int, x: int
    ) -> None:
        self._parent = parent
        self._win: Any | None

        if not parent:
            self._win = None
        else:
            try:
                self._win = parent.derwin(h, w, y, x)
                self._win.noutrefresh()
            except curses.error:
                self._win = None

    def stop(self) -> None:
        del self._win
        self._win = None

    def getbegyx(self) -> tuple[int, int]:
        if not self._win:
            return (0, 0)
        return self._win.getbegyx()

    def getmaxyx(self) -> tuple[int, int]:
        if not self._win:
            return (0, 0)
        return self._win.getmaxyx()
