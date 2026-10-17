import curses
import curses.ascii
import textwrap

from pqcli.ui.curses.event_handler import EventHandler
from pqcli.ui.curses.util import KEYS_CANCEL, Choice
from pqcli.ui.curses.widgets import Menu

from .base_view import BaseView


class MessageView(BaseView):
    """Show a message until it is dismissed."""

    def __init__(self, screen: curses.window, message: str) -> None:
        super().__init__(screen)

        self.message = message
        self.on_close = EventHandler[[]]()

        self.choices: list[Choice] = [
            Choice(
                keys=[curses.ascii.NL, *KEYS_CANCEL],
                desc="[Enter] OK",
                callback=self.on_close,
            ),
        ]

    def start(self) -> None:
        scr_height, scr_width = self.screen.getmaxyx()
        self.screen.erase()
        self.screen.noutrefresh()

        width = max(20, scr_width - 6)
        header = "\n".join(
            "\n".join(textwrap.wrap(line, width) or [""])
            for line in self.message.split("\n")
        )
        self.main_menu = Menu(
            header=header,
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
