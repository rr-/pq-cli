import curses
import curses.ascii
import typing as T

from pqcli.ui.curses.util import KEYS_CYCLE, KEYS_DOWN, KEYS_UP, Choice
from pqcli.ui.curses.widgets.focusable import focus_standout

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

        all_lines = self._header_lines + sum(
            [choice.desc.splitlines() for choice in choices], []
        )

        w = max(map(len, all_lines)) + 1
        h = len(all_lines) + 1
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

    def cycle(self) -> None:
        self._active_choice = (self._active_choice + 1) % len(self._choices)

    def keypress(self, key: int) -> None:
        for choice in self._choices:
            if key in choice.keys:
                choice.callback()
                return

        if key == curses.ascii.NL:
            self._choices[self._active_choice].callback()
        elif key in KEYS_DOWN:
            self.next()
        elif key in KEYS_UP:
            self.prev()
        elif key in KEYS_CYCLE:
            self.cycle()

    def render(self) -> None:
        if not self._pad:
            return

        y = len(self._header_lines) + 1
        for i, choice in enumerate(self._choices):
            self._pad.move(y, 0)
            with focus_standout(i == self._active_choice, self._pad):
                lines = choice.desc.splitlines()
                max_len = max(map(len, lines))
                lines = [line.ljust(max_len) for line in lines]
                self._pad.addstr("\n".join(lines))
            y += len(choice.desc.splitlines())

        self._pad.refresh(
            0,
            0,
            (self._scr_height - self._pad.getmaxyx()[0]) // 2,
            (self._scr_width - self._pad.getmaxyx()[1]) // 2,
            self._scr_height - 1,
            self._scr_width - 1,
        )
