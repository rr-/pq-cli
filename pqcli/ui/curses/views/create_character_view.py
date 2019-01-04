import curses
import curses.ascii
import functools
import typing as T

from pqcli.config import CLASSES, PRIME_STATS, RACES, Class, Race
from pqcli.mechanic import StatsBuilder, generate_name
from pqcli.ui.curses.event_handler import EventHandler
from pqcli.ui.curses.util import Choice
from pqcli.ui.curses.views.base_view import BaseView
from pqcli.ui.curses.views.menu_view import MenuView


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

        h = 1
        w = 30
        y = (scr_height - h - 2) // 2
        x = (scr_width - w - 2) // 2
        self._win = curses.newwin(h + 2, w + 2, y, x)
        self._win.box()
        self.screen.addstr(y - 1, x, "Choose character name:")
        self.screen.addstr(y + h + 2, x, "[ F5  ] generate random name")
        self.screen.addstr(y + h + 3, x, "[ Esc ] cancel")
        self.screen.addstr(y + h + 4, x, "[Enter] confirm")
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


class ChooseCharacterRaceView(MenuView):
    def __init__(self, screen: T.Any, race: T.Optional[Race] = None) -> None:
        super().__init__(
            screen,
            "Choose character race",
            RACES.index(race) if race is not None else 0,
        )

        for y, race in enumerate(RACES, 1):
            key: T.Optional[str] = str(y % 10) if y <= 10 else None
            self._choices.append(
                Choice(
                    keys=[ord(key)] if key is not None else [],
                    desc=f"[{key or '-'}] {race.name}",
                    callback=functools.partial(self.on_confirm, race),
                )
            )

        self._choices.append(
            Choice(
                keys=list(map(ord, "qQ\N{ESC}")),
                desc="[Q] Cancel",
                callback=self.on_cancel,
            )
        )


class ChooseCharacterClassView(MenuView):
    def __init__(
        self, screen: T.Any, class_: T.Optional[Class] = None
    ) -> None:
        super().__init__(
            screen,
            "Choose character class",
            CLASSES.index(class_) if class_ is not None else 0,
        )

        for y, class_ in enumerate(CLASSES, 1):
            key: T.Optional[str] = str(y % 10) if y <= 10 else None
            self._choices.append(
                Choice(
                    keys=[ord(key)] if key is not None else [],
                    desc=f"[{key or '-'}] {class_.name}",
                    callback=functools.partial(self.on_confirm, class_),
                )
            )

        self._choices.append(
            Choice(
                keys=list(map(ord, "qQ\N{ESC}")),
                desc="[Q] Cancel",
                callback=self.on_cancel,
            )
        )


class ChooseCharacterStatsView(BaseView):
    def __init__(self, screen: T.Any) -> None:
        super().__init__(screen)

        self.on_cancel = EventHandler()
        self.on_confirm = EventHandler()

        self._win: T.Optional[T.Any] = None
        self._stats_win: T.Optional[T.Any] = None

        self._stats_builder = StatsBuilder()
        self._stats = self._stats_builder.roll()

    def start(self) -> None:
        scr_height, scr_width = self.screen.getmaxyx()

        h2 = len(PRIME_STATS) + 2
        h = 5 + h2
        w = 30
        y = (scr_height - h - 2) // 2
        x = (scr_width - w - 2) // 2

        self.screen.erase()
        self.screen.noutrefresh()

        self._win = curses.newwin(h, w, y, x)
        self._stats_win = curses.newwin(h2, w, y + 1, x)
        self._render()

    def stop(self) -> None:
        del self._win
        del self._stats_win
        self._win = None
        self._stats_win = None

    def keypress(self, key: int) -> None:
        if key == curses.ascii.ESC or key in map(ord, "qQ"):
            self.on_cancel()

        elif key == curses.ascii.NL:
            self.on_confirm(self._stats)

        elif key == curses.KEY_F5:
            self._stats = self._stats_builder.roll()

        elif key == curses.KEY_F6:
            self._stats = self._stats_builder.unroll()

        self._render()

    def _render(self) -> None:
        if not self._win or not self._stats_win:
            return

        y, x = self._win.getbegyx()
        stats_h = self._stats_win.getmaxyx()[0]

        self._win.erase()
        self._win.addstr(0, 0, "Roll character stats:")
        self._win.addstr(1 + stats_h + 0, 0, "[ F5  ] roll")
        self._win.addstr(1 + stats_h + 1, 0, "[ F6  ] unroll")
        self._win.addstr(1 + stats_h + 2, 0, "[ Esc ] cancel")
        self._win.addstr(1 + stats_h + 3, 0, "[Enter] confirm")
        self._win.noutrefresh()

        self._stats_win.erase()
        for y, stat in enumerate(PRIME_STATS):
            self._stats_win.addstr(
                y + 1, 1, f"{stat.value}: {self._stats[stat]}"
            )
        self._stats_win.box()
        self._stats_win.noutrefresh()

        curses.doupdate()
