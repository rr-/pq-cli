import argparse
import curses
import datetime
import typing as T

from pqcli.mechanic import Player, Simulation
from pqcli.roster import Roster
from pqcli.ui.curses.event_handler import EventHandler

from ..base_view import BaseView
from .character_sheet_window import CharacterSheetWindow
from .equipment_window import EquipmentWindow
from .inventory_window import InventoryWindow
from .plot_window import PlotWindow
from .quest_book_window import QuestBookWindow
from .spell_book_window import SpellBookWindow
from .task_progress_window import TaskProgressWindow


class GameView(BaseView):
    def __init__(
        self,
        screen: T.Any,
        roster: Roster,
        player: Player,
        args: argparse.Namespace,
    ) -> None:
        super().__init__(screen)
        self.on_exit = EventHandler()

        self._roster = roster
        self._player = player
        self._args = args

        self._simulation = Simulation(player)
        self._last_tick = datetime.datetime.now()

    def keypress(self, key: int) -> None:
        if key in map(ord, "qQ"):
            self.on_exit()
        else:
            super().keypress(key)

    def start(self) -> None:
        scr_height, scr_width = self.screen.getmaxyx()
        col1_width = int(scr_width * 0.3)
        col3_width = col1_width
        col2_width = scr_width - col1_width - col3_width

        self.screen.erase()
        self.screen.refresh()

        self._big_win = curses.newwin(scr_height, scr_width)
        self._col1_win = self._big_win.derwin(scr_height - 2, col1_width, 0, 0)
        self._col2_win = self._big_win.derwin(
            self._col1_win.getmaxyx()[0],
            col2_width,
            0,
            self._col1_win.getmaxyx()[1],
        )
        self._col3_win = self._big_win.derwin(
            self._col1_win.getmaxyx()[0],
            col3_width,
            0,
            self._col1_win.getmaxyx()[1] + self._col2_win.getmaxyx()[1],
        )

        self._char_sheet_win = CharacterSheetWindow(
            player=self._player,
            parent=self._col1_win,
            h=min(17, self._col1_win.getmaxyx()[0]),
            w=self._col1_win.getmaxyx()[1],
            y=0,
            x=0,
        )

        self._spell_book_win = SpellBookWindow(
            player=self._player,
            parent=self._col1_win,
            h=self._col1_win.getmaxyx()[0]
            - self._char_sheet_win.getmaxyx()[0],
            w=self._col1_win.getmaxyx()[1],
            y=self._char_sheet_win.getmaxyx()[0],
            x=0,
        )

        self._equipment_win = EquipmentWindow(
            player=self._player,
            parent=self._col2_win,
            h=min(15, self._col2_win.getmaxyx()[0]),
            w=self._col2_win.getmaxyx()[1],
            y=0,
            x=0,
        )

        self._inventory_win = InventoryWindow(
            player=self._player,
            parent=self._col2_win,
            h=max(
                1,
                self._col2_win.getmaxyx()[0]
                - self._equipment_win.getmaxyx()[0],
            ),
            w=self._col2_win.getmaxyx()[1],
            y=self._equipment_win.getmaxyx()[0],
            x=0,
        )

        self._plot_win = PlotWindow(
            player=self._player,
            parent=self._col3_win,
            h=self._equipment_win.getmaxyx()[0],
            w=self._col3_win.getmaxyx()[1],
            y=0,
            x=0,
        )

        self._quest_book_win = QuestBookWindow(
            player=self._player,
            parent=self._col3_win,
            h=max(
                1, self._col3_win.getmaxyx()[0] - self._plot_win.getmaxyx()[0]
            ),
            w=self._col3_win.getmaxyx()[1],
            y=self._plot_win.getmaxyx()[0],
            x=0,
        )

        self._task_win = TaskProgressWindow(
            player=self._player,
            parent=self._big_win,
            h=2,
            w=scr_width,
            y=scr_height - 2,
            x=0,
        )

    def stop(self) -> None:
        self._char_sheet_win.stop()
        self._spell_book_win.stop()
        self._equipment_win.stop()
        self._inventory_win.stop()
        self._plot_win.stop()
        self._quest_book_win.stop()
        self._task_win.stop()
        del self._col1_win
        del self._col2_win
        del self._col3_win
        del self._big_win

    def idle(self) -> None:
        elapsed = datetime.datetime.now() - self._last_tick
        self._simulation.tick(elapsed.total_seconds() * 1000)
        self._last_tick = datetime.datetime.now()
        if self._args.use_saves:
            self._roster.save_periodically()
