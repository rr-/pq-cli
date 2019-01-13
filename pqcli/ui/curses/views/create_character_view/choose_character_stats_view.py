import curses.ascii
import typing as T

from pqcli.config import PRIME_STATS
from pqcli.mechanic import StatsBuilder
from pqcli.ui.curses.event_handler import EventHandler
from pqcli.ui.curses.util import KEYS_CANCEL, KEYS_CYCLE, KEYS_DOWN, KEYS_UP
from pqcli.ui.curses.views.base_view import BaseView
from pqcli.ui.curses.widgets.focusable import focus_standout


class ChooseCharacterStatsView(BaseView):
    def __init__(self, screen: T.Any) -> None:
        super().__init__(screen)

        self.on_cancel = EventHandler()
        self.on_confirm = EventHandler()

        self._active_widget = 0
        self._win: T.Optional[T.Any] = None
        self._stats_win: T.Optional[T.Any] = None

        self._stats_builder = StatsBuilder()
        self._stats = self._stats_builder.roll()

    def start(self) -> None:
        scr_height, scr_width = self.screen.getmaxyx()

        h2 = len(PRIME_STATS) + 2
        h = 7 + h2
        w = 30
        y = (scr_height - h - 2) // 2
        x = (scr_width - w - 2) // 2

        self.screen.erase()
        self.screen.noutrefresh()

        self._win = curses.newwin(h, w, y, x)
        self._stats_win = curses.newwin(h2, w, y + 2, x - 1)
        self._render()

    def stop(self) -> None:
        del self._win
        del self._stats_win
        self._win = None
        self._stats_win = None

    def keypress(self, key: int) -> None:
        if key in KEYS_CANCEL:
            self.on_cancel()

        elif key == curses.ascii.NL:
            if self._active_widget == 0:
                self._stats = self._stats_builder.roll()
            elif self._active_widget == 1:
                self._stats = self._stats_builder.unroll()
            elif self._active_widget == 2:
                self.on_confirm(self._stats)
            elif self._active_widget == 3:
                self.on_cancel()
            else:
                assert False

        elif key == curses.KEY_F5:
            self._stats = self._stats_builder.roll()

        elif key == curses.KEY_F6:
            self._stats = self._stats_builder.unroll()

        elif key == curses.KEY_F10:
            self.on_confirm(self._stats)

        elif key in KEYS_CYCLE:
            self._active_widget = (self._active_widget + 1) % 4

        elif key in KEYS_DOWN and self._active_widget < 3:
            self._active_widget += 1

        elif key in KEYS_UP and self._active_widget > 0:
            self._active_widget -= 1

        self._render()

    def _render(self) -> None:
        if not self._win or not self._stats_win:
            return

        y, x = self._win.getbegyx()
        stats_h = self._stats_win.getmaxyx()[0]

        self._win.erase()
        self._win.addstr(0, 0, "Roll character stats:")
        with focus_standout(self._active_widget == 0, self._win):
            self._win.addstr(3 + stats_h + 0, 0, "[F5   ] Roll")
        with focus_standout(self._active_widget == 1, self._win):
            self._win.addstr(3 + stats_h + 1, 0, "[F6   ] Unroll")
        with focus_standout(self._active_widget == 2, self._win):
            self._win.addstr(3 + stats_h + 2, 0, "[F10  ] Continue")
        with focus_standout(self._active_widget == 3, self._win):
            self._win.addstr(3 + stats_h + 3, 0, "[Esc  ] Cancel")
        self._win.noutrefresh()

        self._stats_win.erase()
        for y, stat in enumerate(PRIME_STATS):
            self._stats_win.addstr(
                y + 1, 1, f"{stat.value}: {self._stats[stat]}"
            )
        self._stats_win.box()
        self._stats_win.noutrefresh()

        curses.doupdate()
