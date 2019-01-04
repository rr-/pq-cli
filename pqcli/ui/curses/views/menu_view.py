import functools
import typing as T

from pqcli.ui.curses.event_handler import EventHandler
from pqcli.ui.curses.util import Choice
from pqcli.ui.curses.views.base_view import BaseView
from pqcli.ui.curses.widgets import Menu


class MenuView(BaseView):
    def __init__(self, screen: T.Any, title: str) -> None:
        super().__init__(screen)

        self.on_cancel = EventHandler()
        self.on_confirm = EventHandler()

        self._title = f"{title}:"
        self._choices: T.List[Choice] = []

    def start(self) -> None:
        scr_height, scr_width = self.screen.getmaxyx()
        self.screen.erase()
        self.screen.noutrefresh()

        self.main_menu = Menu(
            header=self._title,
            choices=self._choices,
            scr_height=scr_height,
            scr_width=scr_width,
        )
        self.main_menu.render()

    def stop(self) -> None:
        self.main_menu.stop()

    def keypress(self, key: int) -> None:
        self.main_menu.keypress(key)
        self.main_menu.render()
