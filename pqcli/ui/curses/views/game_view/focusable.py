import contextlib
import typing as T

from pqcli.ui.curses.event_handler import EventHandler


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
        if self._focused:
            win.standout()
        yield
        if self._focused:
            win.standend()
