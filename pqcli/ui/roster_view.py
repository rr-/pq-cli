import typing as T

import urwid

from pqcli.lingo import act_name, to_roman
from pqcli.roster import Roster
from pqcli.ui.custom_button import CustomButton
from pqcli.ui.layout import NColumns, NPile


class RosterView(urwid.Filler):
    signals = ["load_game", "new_game", "delete_game", "exit"]

    def __init__(self, roster: Roster) -> None:
        self.roster = roster

        logo = urwid.BigText("Progress Quest", urwid.HalfBlock5x4Font())

        buttons = []
        for player_idx, player in enumerate(self.roster.players):
            best_equip = player.equipment.best

            best_spell = player.spell_book.best
            if best_spell:
                best_spell_name = (
                    best_spell.name + " " + to_roman(best_spell.level)
                )
            else:
                best_spell_name = "-"

            best_stat_name = (
                f"{player.stats.best_prime.value} "
                f"{player.stats[player.stats.best_prime]}"
            )

            label = (
                f"{player.name} the {player.race.name} "
                f"({act_name(player.quest_book.act)})\n"
                f"Level {player.level} {player.class_.name}\n"
                f"{best_equip} / {best_spell_name} / {best_stat_name}"
            )

            buttons.append(
                NColumns(
                    [
                        CustomButton(
                            label=label,
                            on_press=self.on_resume_game_press,
                            user_data=player_idx,
                        ),
                        (
                            10,
                            CustomButton(
                                label="Delete",
                                on_press=self.on_delete_game_press,
                                user_data=player_idx,
                            ),
                        ),
                    ]
                )
            )
            buttons.append(urwid.Divider())

        buttons.append(
            CustomButton(
                label="Create a new character",
                hint="F1",
                on_press=self.on_new_game_press,
            )
        )

        buttons.append(
            CustomButton(label="Exit", hint="Esc", on_press=self.on_exit_press)
        )

        super().__init__(
            urwid.Padding(
                NPile(
                    [urwid.Padding(logo, width="clip"), urwid.Divider()]
                    + buttons,
                    outermost=True,
                ),
                align="center",
                width=logo.pack()[0],
            )
        )

    def on_resume_game_press(
        self, _widget: urwid.Widget, user_data: T.Any
    ) -> None:
        player_idx = T.cast(int, user_data)
        self._emit("load_game", player_idx)

    def on_delete_game_press(
        self, _widget: urwid.Widget, user_data: T.Any
    ) -> None:
        player_idx = T.cast(int, user_data)
        self._emit("delete_game", player_idx)

    def on_new_game_press(self, _user_data: T.Any) -> None:
        self._emit("new_game")

    def on_exit_press(self, _user_data: T.Any) -> None:
        self._emit("exit")

    def unhandled_input(self, key: str) -> bool:
        if key == "esc":
            self._emit("exit")
            return True

        if key == "f1":
            self._emit("new_game")
            return True

        return False
