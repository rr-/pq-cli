import curses
import typing as T


class Widget:
    def __del__(self) -> None:
        self.stop()

    def stop(self) -> None:
        pass


class WindowWrapper(Widget):
    def __init__(
        self, parent: T.Optional[T.Any], h: int, w: int, y: int, x: int
    ) -> None:
        self._parent = parent
        self._win: T.Optional[T.Any]

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

    def getbegyx(self) -> T.Tuple[int, int]:
        if not self._win:
            return (0, 0)
        return self._win.getbegyx()

    def getmaxyx(self) -> T.Tuple[int, int]:
        if not self._win:
            return (0, 0)
        return self._win.getmaxyx()
