import argparse
import signal
import curses
import os
import time
import typing as T

from pqcli import lingo
from pqcli.mechanic import Player
from pqcli.roster import Roster
from pqcli.ui.curses.views import (
    BaseView,
    ChooseCharacterView,
    ConfirmView,
    CreateCharacterView,
    GameView,
    RosterView,
)

from ..base import BaseUserInterface


class StopMainLoop(Exception):
    pass


class CursesUserInterface(BaseUserInterface):
    def __init__(self, roster: Roster, args: argparse.Namespace) -> None:
        super().__init__(roster, args)
        os.environ.setdefault("ESCDELAY", "25")
        self.screen = curses.initscr()
        self.screen.nodelay(True)
        self.screen.keypad(True)
        curses.noecho()
        curses.curs_set(0)

        def signal_handler(sig, frame):
            print("Quitting")
            if self.args.use_saves:
                self.roster.save()
            exit(0)

        signal.signal(signal.SIGINT, signal_handler)

        self.roster_view = RosterView(self.screen)
        self.roster_view.on_create += self.switch_to_create_character_view
        self.roster_view.on_delete += self.switch_to_delete_character_view
        self.roster_view.on_play += self.switch_to_play_view
        self.roster_view.on_quit += self.quit
        self.view: BaseView = self.roster_view
        self.view.start()

    def run(self) -> None:
        try:
            self.switch_to_roster_view()

            while True:
                key = T.cast(int, self.screen.getch())

                if key == curses.ERR:
                    time.sleep(0.1)
                    self.view.idle()
                    continue

                if key == curses.KEY_RESIZE:
                    self.view.stop()
                    self.view.start()
                else:
                    try:
                        self.view.keypress(key)
                    except StopMainLoop:
                        break

        finally:
            curses.endwin()
            curses.curs_set(1)

    def switch_to_roster_view(self) -> None:
        self.switch_view(self.roster_view)

    def switch_to_create_character_view(self) -> None:
        view = CreateCharacterView(self.screen)
        view.on_cancel += self.switch_to_roster_view
        view.on_confirm += self.switch_to_game_view
        self.switch_view(view)

    def switch_to_delete_character_view(self) -> None:
        view = ChooseCharacterView(
            self.screen, self.roster, "Choose character to delete"
        )
        view.on_cancel += self.switch_to_roster_view
        view.on_confirm += self.switch_to_confirm_delete_character_view
        self.switch_view(view)

    def switch_to_confirm_delete_character_view(self, player: Player) -> None:
        view = ConfirmView(self.screen, lingo.terminate_message(player.name))
        view.on_cancel += self.switch_to_delete_character_view
        view.on_confirm += lambda: self.delete_character(player)
        self.switch_view(view)

    def switch_to_play_view(self) -> None:
        view = ChooseCharacterView(
            self.screen, self.roster, "Choose character to play"
        )
        view.on_cancel += self.switch_to_roster_view
        view.on_confirm += self.switch_to_game_view
        self.switch_view(view)

    def switch_to_game_view(self, player: Player) -> None:
        view = GameView(self.screen, player)
        view.on_exit += self.switch_to_roster_view
        self.switch_view(view)

    def switch_view(self, view: BaseView) -> None:
        self.view.stop()
        self.view = view
        self.view.start()

    def delete_character(self, player: Player) -> None:
        self.roster.players.remove(player)
        self.switch_to_roster_view()

    def quit(self) -> None:
        raise StopMainLoop
