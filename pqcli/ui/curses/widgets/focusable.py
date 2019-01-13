import contextlib
import curses
import typing as T

from pqcli.ui.curses.colors import COLOR_FOCUSED, has_colors
from pqcli.ui.curses.event_handler import EventHandler


@contextlib.contextmanager
def focus_standout(focused: bool, win: T.Any) -> T.Generator:
    if focused:
        if has_colors():
            win.attron(curses.color_pair(COLOR_FOCUSED))
        else:
            win.standout()
    yield
    if focused:
        if has_colors():
            win.attroff(curses.color_pair(COLOR_FOCUSED))
        else:
            win.standend()


class Focusable:
    def __init__(self, *args: T.Any, **kwargs: T.Any) -> None:
        self._focused = False
        self._on_focus_change = EventHandler()
        super().__init__(*args, **kwargs)

    @property
    def focused(self) -> bool:
        return self._focused

    @focused.setter
    def focused(self, focused: bool) -> None:
        self._focused = focused
        self._on_focus_change()

    @contextlib.contextmanager
    def focus_standout(self, win: T.Any) -> T.Generator:
        with focus_standout(self._focused, win):
            yield
