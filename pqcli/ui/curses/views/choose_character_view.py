import functools
import typing as T

from pqcli.lingo import act_name, to_roman
from pqcli.roster import Roster
from pqcli.ui.curses.event_handler import EventHandler
from pqcli.ui.curses.util import KEYS_CANCEL, Choice
from pqcli.ui.curses.views.menu_view import MenuView
from pqcli.ui.curses.widgets import Menu


class ChooseCharacterView(MenuView):
    def __init__(self, screen: T.Any, roster: Roster, title: str) -> None:
        super().__init__(screen, title)

        for y, player in enumerate(roster.players, 1):
            key: T.Optional[str] = str(y % 10) if y <= 10 else None

            best_equip = player.equipment.best

            best_spell = player.spell_book.best
            best_spell_name = (
                (best_spell.name + " " + to_roman(best_spell.level))
                if best_spell
                else "-"
            )

            best_stat_name = (
                f"{player.stats.best_prime.value} "
                f"{player.stats[player.stats.best_prime]}"
            )

            label = (
                f"[{key or '-'}] "
                f"{player.name} the {player.race.name} "
                f"({act_name(player.quest_book.act)})\n"
                f"    Level {player.level} {player.class_.name}\n"
                f"    {best_equip} / {best_spell_name} / {best_stat_name}"
            )

            self._choices.append(
                Choice(
                    keys=[ord(key)] if key is not None else [],
                    desc=label,
                    callback=functools.partial(self.on_confirm, player),
                )
            )

        self._choices.append(
            Choice(
                keys=list(KEYS_CANCEL),
                desc="[Q] Cancel",
                callback=self.on_cancel,
            )
        )
