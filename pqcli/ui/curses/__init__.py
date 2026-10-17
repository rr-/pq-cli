import argparse
import curses
import os
import signal
from pathlib import Path
from types import FrameType

from pqcli import lingo, pqw
from pqcli.config import Class, Race
from pqcli.game_data import GameData
from pqcli.mechanic import Player, Stats, create_player
from pqcli.random import RngState
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
    MessageView,
    RosterView,
    TextInputView,
)


class StopMainLoop(Exception):
    pass


class CursesUserInterface(BaseUserInterface):
    def __init__(
        self,
        roster: Roster,
        player: Player,
        args: argparse.Namespace,
        data: GameData,
    ) -> None:
        super().__init__(roster, player, args, data)
        os.environ.setdefault("ESCDELAY", "25")
        self._screen = curses.initscr()
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

        def signal_handler(sig: int, frame: FrameType | None) -> None:
            if self.args.use_saves:
                self.roster.save()
            exit(0)

        signal.signal(signal.SIGINT, signal_handler)

        self._roster_view = RosterView(self._screen)
        self._roster_view.on_create += self._switch_to_create_char_name_view
        self._roster_view.on_delete += self._switch_to_delete_char_view
        self._roster_view.on_play += self._switch_to_play_view
        self._roster_view.on_import += self._switch_to_import_view
        self._roster_view.on_export += self._switch_to_export_char_view
        self._roster_view.on_quit += self._quit
        self._view: BaseView = self._roster_view
        self._view.start()
        self._wait_for_keys()

    def run(self) -> None:
        try:
            if self.player:
                self._switch_to_game_view(self.player)
            else:
                self._switch_to_roster_view()

            while True:
                key = self._screen.getch()

                if key == curses.ERR:  # the view's idle interval passed
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
        self, player_name: str | None = None
    ) -> None:
        view = ChooseCharacterNameView(self._screen, player_name)
        view.on_cancel += self._switch_to_roster_view
        view.on_confirm += self._switch_to_create_char_race_view
        self._switch_view(view)

    def _switch_to_create_char_race_view(
        self, player_name: str, race: Race | None = None
    ) -> None:
        view = ChooseCharacterRaceView(self._screen, self.data.races, race)
        view.on_cancel += lambda: self._switch_to_create_char_name_view(
            player_name
        )
        view.on_confirm += lambda race: self._switch_to_create_char_class_view(
            player_name, race
        )
        self._switch_view(view)

    def _switch_to_create_char_class_view(
        self, player_name: str, race: Race, class_: Class | None = None
    ) -> None:
        view = ChooseCharacterClassView(
            self._screen, self.data.classes, class_
        )
        view.on_cancel += lambda: self._switch_to_create_char_race_view(
            player_name, race
        )
        view.on_confirm += lambda class_: (
            self._switch_to_create_char_stats_view(player_name, race, class_)
        )
        self._switch_view(view)

    def _switch_to_create_char_stats_view(
        self, player_name: str, race: Race, class_: Class
    ) -> None:
        view = ChooseCharacterStatsView(self._screen)
        view.on_cancel += lambda: self._switch_to_create_char_class_view(
            player_name, race, class_
        )
        view.on_confirm += lambda stats, seed: self._create_character(
            player_name, race, class_, stats, seed
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

    def _switch_to_import_view(self) -> None:
        view = TextInputView(self._screen, "Import from .pqw file:", "")
        view.on_cancel += self._switch_to_roster_view
        view.on_confirm += self._import_character
        self._switch_view(view)

    def _switch_to_export_char_view(self) -> None:
        view = ChooseCharacterView(
            self._screen, self.roster, "Choose character to export"
        )
        view.on_cancel += self._switch_to_roster_view
        view.on_confirm += self._switch_to_export_file_view
        self._switch_view(view)

    def _switch_to_export_file_view(self, player: Player) -> None:
        view = TextInputView(
            self._screen,
            f"Export {player.name} to .pqw file:",
            pqw.default_file_name(player),
        )
        view.on_cancel += self._switch_to_export_char_view
        view.on_confirm += lambda path: self._export_character(player, path)
        self._switch_view(view)

    def _switch_to_message_view(self, message: str) -> None:
        view = MessageView(self._screen, message)
        view.on_close += self._switch_to_roster_view
        self._switch_view(view)

    def _import_character(self, path: str) -> None:
        try:
            player, warnings = pqw.read_file(
                Path(path).expanduser(), self.data
            )
        except pqw.PqwError as ex:
            self._switch_to_message_view(f"Cannot import: {ex}")
            return
        self.roster.players.append(player)
        if self.args.use_saves:
            self.roster.save()
        self._switch_to_message_view(
            "\n".join([f"Imported {player.name}.", *warnings])
        )

    def _export_character(self, player: Player, path: str) -> None:
        try:
            pqw.write_file(player, Path(path).expanduser(), self.data)
        except pqw.PqwError as ex:
            self._switch_to_message_view(f"Cannot export: {ex}")
            return
        self._switch_to_message_view(f"Exported {player.name} to {path}.")

    def _switch_to_game_view(self, player: Player) -> None:
        view = GameView(
            self._screen, self.roster, player, self.args, self.data
        )
        view.on_exit += self._switch_to_roster_view
        self._switch_view(view)

    def _switch_view(self, view: BaseView) -> None:
        self._view.stop()
        self._view = view
        self._view.start()
        self._wait_for_keys()

    def _wait_for_keys(self) -> None:
        # getch() blocks until a key comes or the view's idle interval
        # passes, so menus sit still and keys never wait for a tick.
        interval = self._view.idle_interval
        self._screen.timeout(-1 if interval is None else interval)

    def _create_character(
        self,
        name: str,
        race: Race,
        class_: Class,
        stats: Stats,
        seed: RngState,
    ) -> None:
        player = create_player(name, race, class_, stats, seed)
        self.roster.players.append(player)
        if self.args.use_saves:
            self.roster.save()
        self._switch_to_game_view(player)

    def _delete_character(self, player: Player) -> None:
        self.roster.players.remove(player)
        self._switch_to_roster_view()

    def _quit(self) -> None:
        raise StopMainLoop
