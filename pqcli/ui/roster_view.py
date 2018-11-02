import typing as T

import urwid

from pqcli.game_state import Roster
from pqcli.ui.button import MenuButton


class RosterView(urwid.Filler):
    def __init__(
        self,
        roster: Roster,
        loop: urwid.MainLoop,
        on_new_game: T.Callable,
        on_resume_game: T.Callable,
        on_exit: T.Callable,
    ) -> None:
        self.roster = roster
        self.on_new_game = on_new_game
        self.on_resume_game = on_resume_game
        self.on_exit = on_exit

        logo = urwid.BigText("ProgressQuest", urwid.HalfBlock5x4Font())

        buttons = []
        for player in self.roster.players:
            buttons.append(
                MenuButton(
                    label=player.name,
                    on_press=self.on_resume_game_press,
                    user_data=player.name,
                )
            )

        buttons.append(
            MenuButton(
                label="Create a new character", on_press=self.on_new_game_press
            )
        )

        buttons.append(MenuButton(label="Exit", on_press=self.on_exit_press))

        super().__init__(
            urwid.Padding(
                urwid.Pile(
                    [urwid.Padding(logo, width="clip"), urwid.Divider()]
                    + buttons
                ),
                align="center",
                width=logo.pack()[0],
            )
        )

    def on_resume_game_press(self, user_data: T.Any) -> None:
        player_name = T.cast(str, user_data)
        self.on_resume_game(player_name)

    def on_new_game_press(self, _user_data: T.Any) -> None:
        self.on_new_game()

    def on_exit_press(self, _user_data: T.Any) -> None:
        self.on_exit()

    def unhandled_input(self, key: str) -> bool:
        if key == "esc":
            self.on_exit()
            return True

        return False
