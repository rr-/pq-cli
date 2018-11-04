import typing as T

import urwid

from pqcli.roster import Roster
from pqcli.ui.button import MenuButton


class RosterView(urwid.Filler):
    signals = ["load_game", "new_game", "delete_game", "exit"]

    def __init__(self, roster: Roster) -> None:
        self.roster = roster

        logo = urwid.BigText("ProgressQuest", urwid.HalfBlock5x4Font())

        buttons = []
        for player_idx, player in enumerate(self.roster.players):
            buttons.append(
                urwid.Columns(
                    [
                        MenuButton(
                            label=player.name,
                            on_press=self.on_resume_game_press,
                            user_data=player_idx,
                        ),
                        (
                            10,
                            MenuButton(
                                label="Delete",
                                on_press=self.on_delete_game_press,
                                user_data=player_idx,
                            ),
                        ),
                    ]
                )
            )

        buttons.append(
            MenuButton(
                label="Create a new character",
                hint="F1",
                on_press=self.on_new_game_press,
            )
        )

        buttons.append(
            MenuButton(label="Exit", hint="Esc", on_press=self.on_exit_press)
        )

        super().__init__(
            urwid.Padding(
                urwid.Pile(
                    [urwid.Padding(logo, width="clip"), urwid.Divider()]
                    + buttons
                    + [
                        urwid.Divider(),
                        urwid.Text("Use arrow keys to move around."),
                    ]
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
