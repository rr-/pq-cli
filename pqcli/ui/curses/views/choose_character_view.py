import functools
import typing as T

from pqcli.roster import Roster

from ..event_handler import EventHandler
from ..util import Choice
from ..widgets import Menu
from .base_view import BaseView


class ChooseCharacterView(BaseView):
    def __init__(self, screen: T.Any, roster: Roster, title: str) -> None:
        super().__init__(screen)

        self.title = f"{title}:"
        self.on_cancel = EventHandler()
        self.on_confirm = EventHandler()

        self.choices: T.List[Choice] = []
        for y, player in enumerate(roster.players, 1):
            key: T.Optional[str] = str(y % 10) if y <= 10 else None
            self.choices.append(
                Choice(
                    keys=[ord(key)] if key is not None else [],
                    desc=f"[{key or '-'}] {player.name}",
                    callback=functools.partial(self.on_confirm, player),
                )
            )
        self.choices.append(
            Choice(
                keys=list(map(ord, "qQ\N{ESC}")),
                desc="[Q] Cancel",
                callback=self.on_cancel,
            )
        )

    def start(self) -> None:
        scr_height, scr_width = self.screen.getmaxyx()
        self.screen.erase()
        self.screen.noutrefresh()

        self.main_menu = Menu(
            header=self.title,
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
