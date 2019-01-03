import typing as T

from ..event_handler import EventHandler
from ..util import Choice
from ..widgets import Menu
from .base_view import BaseView

LOGO = """
█▀▀▄                                    ▄▀▀▄                 █
█▄▄▀ █▀▀ ▄▀▀▄ ▄▀▀▄ █▀▀ ▄▀▀▄ ▄▀▀▀ ▄▀▀▀   █  █ █  █ ▄▀▀▄ ▄▀▀▀ ▀█▀
█    █   █  █ ▀▄▄█ █   █▀▀   ▀▀▄  ▀▀▄   █ ▌█ █  █ █▀▀   ▀▀▄  █
▀    ▀    ▀▀   ▄▄▀ ▀    ▀▀  ▀▀▀  ▀▀▀     ▀▀▌  ▀▀   ▀▀  ▀▀▀    ▀
""".strip()


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
                keys=list(map(ord, "qQ\N{ESC}")),
                desc="[Q] Quit",
                callback=self.on_quit,
            ),
        ]

    def start(self) -> None:
        scr_height, scr_width = self.screen.getmaxyx()
        self.screen.erase()
        self.screen.noutrefresh()

        self.main_menu = Menu(
            header=LOGO,
            choices=self.choices,
            scr_height=scr_height,
            scr_width=scr_width,
        )
        self.main_menu.render()

    def stop(self) -> None:
        self.main_menu.stop()

    def keypress(self, key: int) -> None:
        self.main_menu.keypress(key)
        self.main_menu.render()
