import argparse
import curses
import os
import signal
import time
import typing as T

from pqcli import lingo
from pqcli.config import Class, Race
from pqcli.mechanic import Player, Stats, create_player
from pqcli.roster import Roster
from pqcli.ui.base import BaseUserInterface
from pqcli.ui.curses.colors import (
    COLOR_FOCUSED,
    COLOR_HIGHLIGHT,
    COLOR_LOGO,
    COLOR_LOGO_ALT,
    COLOR_PROGRESSBAR,
    COLOR_SCROLLBAR_THUMB,
    COLOR_SCROLLBAR_TRACK,
    has_colors,
    set_colors,
)
from pqcli.ui.curses.views import (
    BaseView,
    ChooseCharacterClassView,
    ChooseCharacterNameView,
    ChooseCharacterRaceView,
    ChooseCharacterStatsView,
    ChooseCharacterView,
    ConfirmView,
    GameView,
    RosterView,
)


class StopMainLoop(Exception):
    pass


class CursesUserInterface(BaseUserInterface):
    def __init__(self, roster: Roster, args: argparse.Namespace) -> None:
        super().__init__(roster, args)
        os.environ.setdefault("ESCDELAY", "25")
        self._screen = curses.initscr()
        self._screen.nodelay(True)
        self._screen.keypad(True)
        curses.noecho()
        curses.curs_set(0)

        set_colors(args.colors)
        if has_colors():
            curses.start_color()
            curses.use_default_colors()
            curses.init_pair(COLOR_LOGO, -1, -1)
            curses.init_pair(COLOR_LOGO_ALT, -1, 9)
            curses.init_pair(COLOR_FOCUSED, -1, 8)
            curses.init_pair(COLOR_SCROLLBAR_THUMB, -1, 7)
            curses.init_pair(COLOR_SCROLLBAR_TRACK, -1, 0)
            curses.init_pair(COLOR_PROGRESSBAR, 0, 9)
            curses.init_pair(COLOR_HIGHLIGHT, 3, -1)

        def signal_handler(sig: T.Any, frame: T.Any) -> None:
            if self.args.use_saves:
                self.roster.save()
            exit(0)

        signal.signal(signal.SIGINT, signal_handler)

        self._roster_view = RosterView(self._screen)
        self._roster_view.on_create += self._switch_to_create_char_name_view
        self._roster_view.on_delete += self._switch_to_delete_char_view
        self._roster_view.on_play += self._switch_to_play_view
        self._roster_view.on_quit += self._quit
        self._view: BaseView = self._roster_view
        self._view.start()

    def run(self) -> None:
        try:
            self._switch_to_roster_view()

            while True:
                key = T.cast(int, self._screen.getch())

                if key == curses.ERR:
                    time.sleep(0.1)
                    self._view.idle()
                    continue

                if key == curses.KEY_RESIZE:
                    self._view.stop()
                    self._view.start()
                else:
                    try:
                        self._view.keypress(key)
                    except StopMainLoop:
                        break

        finally:
            curses.endwin()
            curses.curs_set(1)

    def _switch_to_roster_view(self) -> None:
        self._switch_view(self._roster_view)

    def _switch_to_create_char_name_view(
        self, player_name: T.Optional[str] = None
    ) -> None:
        view = ChooseCharacterNameView(self._screen, player_name)
        view.on_cancel += self._switch_to_roster_view
        view.on_confirm += self._switch_to_create_char_race_view
        self._switch_view(view)

    def _switch_to_create_char_race_view(
        self, player_name: str, race: T.Optional[Race] = None
    ) -> None:
        view = ChooseCharacterRaceView(self._screen, race)
        view.on_cancel += lambda: self._switch_to_create_char_name_view(
            player_name
        )
        view.on_confirm += lambda race: self._switch_to_create_char_class_view(
            player_name, race
        )
        self._switch_view(view)

    def _switch_to_create_char_class_view(
        self, player_name: str, race: Race, class_: T.Optional[Class] = None
    ) -> None:
        view = ChooseCharacterClassView(self._screen, class_)
        view.on_cancel += lambda: self._switch_to_create_char_race_view(
            player_name, race
        )
        view.on_confirm += lambda class_: self._switch_to_create_char_stats_view(
            player_name, race, class_
        )
        self._switch_view(view)

    def _switch_to_create_char_stats_view(
        self, player_name: str, race: Race, class_: Class
    ) -> None:
        view = ChooseCharacterStatsView(self._screen)
        view.on_cancel += lambda: self._switch_to_create_char_class_view(
            player_name, race, class_
        )
        view.on_confirm += lambda stats: self._create_character(
            player_name, race, class_, stats
        )
        self._switch_view(view)

    def _switch_to_delete_char_view(self) -> None:
        view = ChooseCharacterView(
            self._screen, self.roster, "Choose character to delete"
        )
        view.on_cancel += self._switch_to_roster_view
        view.on_confirm += self._switch_to_confirm_delete_char_view
        self._switch_view(view)

    def _switch_to_confirm_delete_char_view(self, player: Player) -> None:
        view = ConfirmView(self._screen, lingo.terminate_message(player.name))
        view.on_cancel += self._switch_to_delete_char_view
        view.on_confirm += lambda: self._delete_character(player)
        self._switch_view(view)

    def _switch_to_play_view(self) -> None:
        view = ChooseCharacterView(
            self._screen, self.roster, "Choose character to play"
        )
        view.on_cancel += self._switch_to_roster_view
        view.on_confirm += self._switch_to_game_view
        self._switch_view(view)

    def _switch_to_game_view(self, player: Player) -> None:
        view = GameView(self._screen, self.roster, player, self.args)
        view.on_exit += self._switch_to_roster_view
        self._switch_view(view)

    def _switch_view(self, view: BaseView) -> None:
        self._view.stop()
        self._view = view
        self._view.start()

    def _create_character(
        self, name: str, race: Race, class_: Class, stats: Stats
    ) -> None:
        player = create_player(name, race, class_, stats)
        self.roster.players.append(player)
        if self.args.use_saves:
            self.roster.save()
        self._switch_to_game_view(player)

    def _delete_character(self, player: Player) -> None:
        self.roster.players.remove(player)
        self._switch_to_roster_view()

    def _quit(self) -> None:
        raise StopMainLoop
