import argparse
import typing as T

import urwid

from pqcli import random
from pqcli.mechanic import Player
from pqcli.roster import Roster
from pqcli.ui.confirm_dialog import ConfirmDialog
from pqcli.ui.game_view import GameView
from pqcli.ui.new_game_view import NewGameView
from pqcli.ui.roster_view import RosterView


PALETTE: T.List[T.Tuple[str, str, str]] = [
    ("button", "", ""),
    ("button-focus", "light red", "black"),
    ("linebox", "", ""),
    ("linebox-focus", "light red", "black"),
    ("linebox-content", "", ""),
    ("linebox-content-focus", "", ""),
    ("progressbar-normal", "", "", "standout"),
    ("progressbar-done", "black", "light red"),
    ("progressbar-smooth", "light red", ""),
]


class ConfirmExitDialog(ConfirmDialog):
    def __init__(self, old_view: urwid.Widget) -> None:
        super().__init__("Really quit?", old_view)


def bind_commands() -> None:
    for key, direction in {
        "k": "up",
        "j": "down",
        "h": "left",
        "l": "right",
    }.items():
        for key_variant in {key, key.upper()}:
            urwid.command_map[key_variant] = f"cursor {direction}"
    urwid.command_map["tab"] = f"cursor down"
    urwid.command_map["shift tab"] = f"cursor up"


class Ui:
    def __init__(self, roster: Roster, args: argparse.Namespace) -> None:
        bind_commands()

        self.roster = roster
        self.args = args
        self.loop = urwid.MainLoop(
            None, PALETTE, unhandled_input=self.unhandled_input
        )
        self.old_views: T.List[urwid.Widget] = []

        self.switch_to_roster_view()

    def run(self) -> None:
        self.loop.run()

    def unhandled_input(self, key: str) -> bool:
        callback = getattr(self.loop.widget, "unhandled_input", None)
        if callback and callback(key):
            return True

        if key == "ctrl q":
            self.switch_to_exit_view()
            return True

        return False

    def switch_to_roster_view(self) -> None:
        self.loop.widget = RosterView(self.roster)
        self._connect("load_game", self.switch_to_game_view)
        self._connect("new_game", self.switch_to_new_game_view)
        self._connect("delete_game", self.switch_to_delete_player_view)
        self._connect("exit", self.switch_to_exit_view)

    def switch_to_exit_view(self) -> None:
        if isinstance(self.loop.widget, ConfirmExitDialog):
            return
        self.old_views.append(self.loop.widget)
        self.loop.widget = ConfirmExitDialog(self.old_views[-1])
        self._connect("confirm", self.exit)
        self._connect("cancel", self.cancel_dialog)

    def switch_to_new_game_view(self) -> None:
        self.loop.widget = NewGameView()
        self._connect("confirm", self.create_player)
        self._connect("cancel", self.switch_to_roster_view)

    def create_player(self, player: Player) -> None:
        self.roster.add_player(player)
        self.switch_to_roster_view()

    def delete_player(self, player_idx: int) -> None:
        self.roster.delete_player_at(player_idx)
        self.switch_to_roster_view()

    def switch_to_game_view(self, player_idx: int) -> None:
        player = self.roster.players[player_idx]
        self.loop.widget = GameView(self.loop, player, self.args)
        self._connect("cancel", self.switch_to_roster_view)

    def switch_to_delete_player_view(self, player_idx: int) -> None:
        adjective = random.choice(["faithful", "noble", "loyal", "brave"])
        player_name = self.roster.players[player_idx].name

        self.old_views.append(self.loop.widget)
        self.loop.widget = ConfirmDialog(
            f"Terminate {adjective} {player_name}?", self.old_views[-1]
        )
        self._connect("confirm", lambda: self.delete_player(player_idx))
        self._connect("cancel", self.cancel_dialog)

    def exit(self) -> None:
        raise urwid.ExitMainLoop()

    def cancel_dialog(self) -> None:
        assert len(self.old_views)
        self.loop.widget = self.old_views.pop()

    def _connect(self, signal_name: str, callback: T.Callable) -> None:
        urwid.signals.connect_signal(
            self.loop.widget,
            signal_name,
            lambda _sender, *args: callback(*args),
        )
