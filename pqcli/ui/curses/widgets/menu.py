import curses
import curses.ascii
import typing as T

from pqcli.ui.curses.util import KEYS_DOWN, KEYS_UP

from ..util import Choice
from .base import Widget


class Menu(Widget):
    def __init__(
        self,
        header: str,
        choices: T.List[Choice],
        active_choice: int,
        scr_height: int,
        scr_width: int,
    ) -> None:
        self._header_lines = header.split("\n")
        self._choices = choices
        self._scr_width = scr_width
        self._scr_height = scr_height

        w = max(map(len, self._header_lines))
        h = len(self._header_lines) + 1 + len(choices)
        self._pad: T.Optional[T.Any] = curses.newpad(h, w)

        for y, line in enumerate(self._header_lines):
            self._pad.move(y, 0)
            self._pad.addstr(line)

        self._active_choice = active_choice

    def stop(self) -> None:
        del self._pad
        self._pad = None

    def getmaxyx(self) -> T.Tuple[int, int]:
        if not self._pad:
            return (0, 0)
        return self._pad.getmaxyx()

    def next(self) -> None:
        self._active_choice = min(
            len(self._choices) - 1, self._active_choice + 1
        )

    def prev(self) -> None:
        self._active_choice = max(0, self._active_choice - 1)

    def keypress(self, key: int) -> None:
        for choice in self._choices:
            if key in choice.keys:
                choice.callback()
                return

        if key == curses.ascii.NL:
            self._choices[self._active_choice].callback()
            return

        if key in KEYS_DOWN:
            self.next()
            return

        if key in KEYS_UP:
            self.prev()
            return

    def render(self) -> None:
        if not self._pad:
            return

        for y, choice in enumerate(self._choices):
            self._pad.move(len(self._header_lines) + 1 + y, 0)
            if y == self._active_choice:
                self._pad.standout()
            self._pad.addstr(choice.desc)
            if y == self._active_choice:
                self._pad.standend()

        self._pad.refresh(
            0,
            0,
            (self._scr_height - self._pad.getmaxyx()[0]) // 2,
            (self._scr_width - self._pad.getmaxyx()[1]) // 2,
            self._scr_height - 1,
            self._scr_width - 1,
        )
