import curses
import curses.ascii
import typing as T

from pqcli.mechanic import generate_name
from pqcli.ui.curses.event_handler import EventHandler
from pqcli.ui.curses.util import KEYS_CANCEL, KEYS_CYCLE, KEYS_DOWN, KEYS_UP
from pqcli.ui.curses.views.base_view import BaseView
from pqcli.ui.curses.widgets.focusable import focus_standout


class ChooseCharacterNameView(BaseView):
    def __init__(
        self, screen: T.Any, character_name: T.Optional[str] = None
    ) -> None:
        super().__init__(screen)

        self.on_cancel = EventHandler()
        self.on_confirm = EventHandler()

        self._active_widget = 0
        self._win: T.Optional[T.Any] = None
        self._text_win: T.Optional[T.Any] = None
        self._text = character_name or generate_name()

    def start(self) -> None:
        self.screen.erase()
        self.screen.noutrefresh()

        scr_height, scr_width = self.screen.getmaxyx()

        h = 8
        w = 30
        y = (scr_height - h - 2) // 2
        x = (scr_width - w - 2) // 2
        self._text_win = curses.newwin(3, w + 2, y + 2, x - 1)
        self._win = curses.newwin(h + 2, w + 2, y, x)

        self._render()

    def stop(self) -> None:
        del self._win
        del self._text_win
        self._win = None
        self._text_win = None

    def keypress(self, key: int) -> None:
        if key == curses.KEY_F5:
            self._text = generate_name()

        elif key == curses.KEY_F10:
            self._finish()

        elif key in KEYS_CYCLE:
            self._active_widget = (self._active_widget + 1) % 4

        elif self._active_widget == 0:
            if key == curses.ascii.ESC:
                self.on_cancel()
            elif curses.ascii.isprint(key):
                self._text += chr(key)
            elif key == curses.KEY_BACKSPACE or key == curses.ascii.DEL:
                self._text = self._text[:-1]
            elif key == curses.ascii.NL:
                self._finish()
            elif key == curses.ascii.ETB:  # ^w
                self._text = ""
            elif key == curses.KEY_DOWN:
                self._active_widget = 1

        else:
            if key == curses.ascii.NL:
                if self._active_widget == 1:
                    self._text = generate_name()
                elif self._active_widget == 2:
                    self._finish()
                elif self._active_widget == 3:
                    self.on_cancel()
                else:
                    assert False

            elif key in KEYS_CANCEL:
                self.on_cancel()

            elif key in KEYS_DOWN and self._active_widget < 3:
                self._active_widget += 1

            elif key in KEYS_UP and self._active_widget > 0:
                self._active_widget -= 1

        self._render()

    def _finish(self) -> None:
        self._text = self._text.strip()
        if self._text:
            self.on_confirm(self._text)
        else:
            self.on_cancel()

    def _render(self) -> None:
        if not self._win or not self._text_win:
            return

        self._win.erase()
        self._win.addstr(0, 0, "Choose character name:")
        with focus_standout(self._active_widget == 1, self._win):
            self._win.addstr(6, 0, "[F5   ] Generate random name")
        with focus_standout(self._active_widget == 2, self._win):
            self._win.addstr(7, 0, "[F10  ] Continue")
        with focus_standout(self._active_widget == 3, self._win):
            self._win.addstr(8, 0, "[Esc  ] Cancel")
        self._win.refresh()

        self._text_win.erase()
        with focus_standout(self._active_widget == 0, self._text_win):
            self._text_win.box()
        self._text_win.addnstr(
            1, 1, self._text, self._text_win.getmaxyx()[1] - 2
        )
        self._text_win.refresh()
