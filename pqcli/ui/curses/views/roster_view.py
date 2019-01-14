import curses
import typing as T

from pqcli.ui.curses.colors import COLOR_LOGO, COLOR_LOGO_ALT, has_colors
from pqcli.ui.curses.event_handler import EventHandler
from pqcli.ui.curses.util import KEYS_CANCEL, Choice
from pqcli.ui.curses.widgets import Menu

from .base_view import BaseView

LOGO = """
                       █▀▀▄         ▄▀▀█
                       ▀▄  ▀▄     ▄▀  ▄▀
                         ▀▄  ▀▄ ▄▀  ▄▀
                           ▀▄ ▄▀  ▄▀
                            ▄▀  ▄▀▄
                       ▄▄▄▄▀  ▄▀▄  ▀▄▄▄▄
                       ▀▄ █▄▄▀   ▀▄▄█ ▄▀
                       ▄▀█▄ █     █ ▄█▀▄
                    ▄▄▀▄▀  ▀▀     ▀▀  ▀▄▀▄▄
                    █▄█                 █▄█

█▀▀▄                                    ▄▀▀▄                 █
█▄▄▀ █▀▀ ▄▀▀▄ ▄▀▀▄ █▀▀ ▄▀▀▄ ▄▀▀▀ ▄▀▀▀   █  █ █  █ ▄▀▀▄ ▄▀▀▀ ▀█▀
█    █   █  █ ▀▄▄█ █   █▀▀   ▀▀▄  ▀▀▄   █ ▌█ █  █ █▀▀   ▀▀▄  █
▀    ▀    ▀▀   ▄▄▀ ▀    ▀▀  ▀▀▀  ▀▀▀     ▀▀▌  ▀▀   ▀▀  ▀▀▀    ▀
""".strip(
    "\n"
)


class MainMenu(Menu):
    def __init__(
        self, choices: T.List[Choice], scr_height: int, scr_width: int
    ) -> None:
        super().__init__(
            header=LOGO,
            choices=choices,
            active_choice=0,
            scr_height=scr_height,
            scr_width=scr_width,
        )
        if has_colors():
            for y in range(len(self._header_lines)):
                self._pad.chgat(y, 0, curses.color_pair(COLOR_LOGO))
            self._pad.chgat(3, 29, 5, curses.color_pair(COLOR_LOGO_ALT))
            self._pad.chgat(4, 29, 5, curses.color_pair(COLOR_LOGO_ALT))
            self._pad.chgat(5, 32, 4, curses.color_pair(COLOR_LOGO_ALT))
            self._pad.chgat(5, 27, 4, curses.color_pair(COLOR_LOGO_ALT))
            self._pad.chgat(6, 34, 2, curses.color_pair(COLOR_LOGO_ALT))
            self._pad.chgat(6, 27, 2, curses.color_pair(COLOR_LOGO_ALT))


class RosterView(BaseView):
    def __init__(self, screen: T.Any) -> None:
        super().__init__(screen)

        self.on_create = EventHandler()
        self.on_play = EventHandler()
        self.on_delete = EventHandler()
        self.on_quit = EventHandler()

        self.choices: T.List[Choice] = [
            Choice(
                keys=list(map(ord, "cC")),
                desc="[C] Create new character",
                callback=self.on_create,
            ),
            Choice(
                keys=list(map(ord, "pP")),
                desc="[P] Play",
                callback=self.on_play,
            ),
            Choice(
                keys=list(map(ord, "dD")),
                desc="[D] Delete character",
                callback=self.on_delete,
            ),
            Choice(
                keys=list(KEYS_CANCEL), desc="[Q] Quit", callback=self.on_quit
            ),
        ]

    def start(self) -> None:
        scr_height, scr_width = self.screen.getmaxyx()
        self.screen.erase()
        self.screen.noutrefresh()

        self.main_menu = MainMenu(
            choices=self.choices, scr_height=scr_height, scr_width=scr_width
        )
        self.main_menu.render()

    def stop(self) -> None:
        self.main_menu.stop()

    def keypress(self, key: int) -> None:
        self.main_menu.keypress(key)
        self.main_menu.render()
