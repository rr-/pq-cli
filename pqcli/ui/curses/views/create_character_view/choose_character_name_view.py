import curses
import curses.ascii
import typing as T

from pqcli.mechanic import generate_name
from pqcli.ui.curses.event_handler import EventHandler
from pqcli.ui.curses.util import KEYS_CANCEL
from pqcli.ui.curses.views.base_view import BaseView


class ChooseCharacterNameView(BaseView):
    def __init__(
        self, screen: T.Any, character_name: T.Optional[str] = None
    ) -> None:
        super().__init__(screen)

        self.on_cancel = EventHandler()
        self.on_confirm = EventHandler()

        self._win: T.Optional[T.Any] = None
        self._text = character_name or generate_name()

    def start(self) -> None:
        self.screen.erase()
        self.screen.noutrefresh()

        scr_height, scr_width = self.screen.getmaxyx()

        h = 8
        w = 30
        y = (scr_height - h - 2) // 2
        x = (scr_width - w - 2) // 2
        self._win = curses.newwin(3, w + 2, y + 2, x - 1)
        self._win.box()
        self.screen.addstr(y, x, "Choose character name:")
        self.screen.addstr(y + 6, x, "[F5   ] generate random name")
        self.screen.addstr(y + 7, x, "[Esc  ] cancel")
        self.screen.addstr(y + 8, x, "[Enter] confirm")
        self._win.refresh()
        self._render()

    def stop(self) -> None:
        del self._win
        self._win = None

    def keypress(self, key: int) -> None:
        if key == curses.ascii.ESC:
            self.on_cancel()

        elif key == curses.KEY_F5:
            self._text = generate_name()

        elif curses.ascii.isprint(key):
            self._text += chr(key)

        elif key == curses.KEY_BACKSPACE or key == curses.ascii.DEL:
            self._text = self._text[:-1]

        elif key == curses.ascii.NL:
            self._text = self._text.strip()
            if self._text:
                self.on_confirm(self._text)
            else:
                self.on_cancel()

        elif key == curses.ascii.ETB:  # ^w
            self._text = ""

        self._render()

    def _render(self) -> None:
        if not self._win:
            return

        self._win.erase()
        self._win.box()
        self._win.addnstr(1, 1, self._text, self._win.getmaxyx()[1] - 2)
        self._win.refresh()
