import functools
import typing as T

from pqcli.roster import Roster
from pqcli.ui.curses.event_handler import EventHandler
from pqcli.ui.curses.util import Choice
from pqcli.ui.curses.views.menu_view import MenuView
from pqcli.ui.curses.widgets import Menu


class ChooseCharacterView(MenuView):
    def __init__(self, screen: T.Any, roster: Roster, title: str) -> None:
        super().__init__(screen, title)

        for y, player in enumerate(roster.players, 1):
            key: T.Optional[str] = str(y % 10) if y <= 10 else None
            self._choices.append(
                Choice(
                    keys=[ord(key)] if key is not None else [],
                    desc=f"[{key or '-'}] {player.name}",
                    callback=functools.partial(self.on_confirm, player),
                )
            )

        self._choices.append(
            Choice(
                keys=list(map(ord, "qQ\N{ESC}")),
                desc="[Q] Cancel",
                callback=self.on_cancel,
            )
        )
