import typing as T

from pqcli.ui.curses.event_handler import EventHandler
from pqcli.ui.curses.util import Choice
from pqcli.ui.curses.widgets import Menu

from .base_view import BaseView


class ConfirmView(BaseView):
    def __init__(self, screen: T.Any, title: str) -> None:
        super().__init__(screen)

        self.title = f"{title}:"
        self.on_cancel = EventHandler()
        self.on_confirm = EventHandler()

        self.choices: T.List[Choice] = [
            Choice(
                keys=list(map(ord, "yY")),
                desc=f"[Y] Yes",
                callback=self.on_confirm,
            ),
            Choice(
                keys=list(map(ord, "nNqQ\N{ESC}")),
                desc="[N] No",
                callback=self.on_cancel,
            ),
        ]

    def start(self) -> None:
        scr_height, scr_width = self.screen.getmaxyx()
        self.screen.erase()
        self.screen.noutrefresh()

        self.main_menu = Menu(
            header=self.title,
            choices=self.choices,
            active_choice=0,
            scr_height=scr_height,
            scr_width=scr_width,
        )
        self.main_menu.render()

    def stop(self) -> None:
        self.main_menu.stop()

    def keypress(self, key: int) -> None:
        self.main_menu.keypress(key)
        self.main_menu.render()
