import functools
import typing as T

from pqcli.config import RACES, Race
from pqcli.ui.curses.util import KEYS_CANCEL, Choice
from pqcli.ui.curses.views.menu_view import MenuView


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
                keys=list(KEYS_CANCEL),
                desc="[Q] Cancel",
                callback=self.on_cancel,
            )
        )
