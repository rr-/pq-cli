import curses
import curses.ascii

from pqcli.ui.curses.event_handler import EventHandler
from pqcli.ui.curses.views.base_view import BaseView


class TextInputView(BaseView):
    """Ask for one line of text, such as a file name."""

    def __init__(self, screen: curses.window, title: str, text: str) -> None:
        super().__init__(screen)

        self.on_cancel = EventHandler[[]]()
        self.on_confirm = EventHandler[[str]]()

        self._title = title
        self._text = text
        self._win: curses.window | None = None
        self._text_win: curses.window | None = None

    def start(self) -> None:
        self.screen.erase()
        self.screen.noutrefresh()

        scr_height, scr_width = self.screen.getmaxyx()
        h = 6
        w = min(60, scr_width - 4)
        y = (scr_height - h - 2) // 2
        x = (scr_width - w - 2) // 2
        self._win = curses.newwin(h + 2, w + 2, y, x)
        self._text_win = curses.newwin(3, w + 2, y + 2, x - 1)
        self._render()

    def stop(self) -> None:
        self._win = None
        self._text_win = None

    def keypress(self, key: int) -> None:
        if key == curses.ascii.ESC:
            self.on_cancel()
            return
        if key == curses.ascii.NL:
            text = self._text.strip()
            if text:
                self.on_confirm(text)
            else:
                self.on_cancel()
            return
        if key in {curses.KEY_BACKSPACE, curses.ascii.DEL}:
            self._text = self._text[:-1]
        elif key == curses.ascii.ETB:  # ^w
            self._text = ""
        elif curses.ascii.isprint(key):
            self._text += chr(key)
        self._render()

    def _render(self) -> None:
        if not self._win or not self._text_win:
            return

        self._win.erase()
        self._win.addstr(0, 0, self._title)
        self._win.addstr(5, 0, "[Enter] Continue")
        self._win.addstr(6, 0, "[Esc  ] Cancel")
        self._win.refresh()

        width = self._text_win.getmaxyx()[1] - 2
        self._text_win.erase()
        self._text_win.box()
        # keep the end of long paths in view
        self._text_win.addnstr(1, 1, self._text[-width + 1 :], width)
        self._text_win.refresh()
