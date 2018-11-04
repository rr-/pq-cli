import typing as T

import urwid

from pqcli.mechanic import Roster
from pqcli.ui.exit_view import ExitView
from pqcli.ui.new_game_view import NewGameView
from pqcli.ui.roster_view import RosterView


PALETTE: T.List[T.Tuple[str, str, str]] = [
    ("button", "", ""),
    ("button-focus", "light red", "black"),
    ("linebox", "", ""),
    ("linebox-focus", "light red", "black"),
    ("linebox-content", "", ""),
    ("linebox-content-focus", "", ""),
]


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
    def __init__(self, roster: Roster) -> None:
        bind_commands()

        self.roster = roster
        self.loop = urwid.MainLoop(
            None, PALETTE, unhandled_input=self.unhandled_input
        )
        self.old_view: T.Optional[urwid.Widget] = None

        self.switch_to_roster_view()

    def run(self) -> None:
        self.loop.run()

    def unhandled_input(self, key: str) -> bool:
        callback = getattr(self.loop.widget, "unhandled_input", None)
        if callback and callback(key):
            return True

        if key == "ctrl q":
            self.old_view = self.loop.widget
            self.switch_to_exit_view()
            return True

        return False

    def switch_to_roster_view(self) -> None:
        self.loop.widget = RosterView(self.roster)
        self._connect("load_game", self.switch_to_game_view)
        self._connect("new_game", self.switch_to_new_game_view)
        self._connect("exit", self.switch_to_exit_view)

    def switch_to_exit_view(self) -> None:
        self.old_view = self.loop.widget
        self.loop.widget = ExitView(self.old_view)
        self._connect("exit", self.exit)
        self._connect("cancel", self.cancel_exit)

    def switch_to_new_game_view(self) -> None:
        self.loop.widget = NewGameView()
        self._connect("confirm", self.switch_to_game_view)
        self._connect("cancel", self.switch_to_roster_view)

    def switch_to_game_view(self, player_name: str) -> None:
        raise NotImplementedError("not implemented")

    def exit(self) -> None:
        raise urwid.ExitMainLoop()

    def cancel_exit(self) -> None:
        assert self.old_view is not None
        self.loop.widget = self.old_view
        self.old_view = None

    def _connect(self, signal_name: str, callback: T.Callable) -> None:
        urwid.signals.connect_signal(
            self.loop.widget,
            signal_name,
            lambda _sender, *args: callback(*args),
        )
