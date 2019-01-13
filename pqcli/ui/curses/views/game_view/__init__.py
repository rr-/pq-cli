import argparse
import curses
import datetime
import typing as T

from pqcli.mechanic import Player, SignalMixin, Simulation
from pqcli.roster import Roster
from pqcli.ui.curses.event_handler import EventHandler
from pqcli.ui.curses.util import (
    KEYS_CANCEL,
    KEYS_CYCLE,
    KEYS_DOWN,
    KEYS_LEFT,
    KEYS_RIGHT,
    KEYS_UP,
)
from pqcli.ui.curses.views.base_view import BaseView
from pqcli.ui.curses.widgets import Focusable, Scrollable, Widget

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
        focused = self.focused

        if key in KEYS_CANCEL:
            self.on_exit()

        elif key in {curses.KEY_PPAGE}:
            if hasattr(focused, "scroll_page_up"):
                focused.scroll_page_up()

        elif key in {curses.KEY_NPAGE}:
            if hasattr(focused, "scroll_page_down"):
                focused.scroll_page_down()

        elif key in KEYS_CYCLE:
            if focused == self._char_sheet_win:
                self.focus(self._spell_book_win)
            elif focused == self._spell_book_win:
                self.focus(self._equipment_win)
            elif focused == self._equipment_win:
                self.focus(self._inventory_win)
            elif focused == self._inventory_win:
                self.focus(self._plot_win)
            elif focused == self._plot_win:
                self.focus(self._quest_book_win)
            elif focused == self._quest_book_win:
                self.focus(self._char_sheet_win)

        elif key in KEYS_DOWN:
            if focused == self._char_sheet_win:
                self.focus(self._spell_book_win)
            elif focused == self._equipment_win:
                self.focus(self._inventory_win)
            elif focused == self._plot_win:
                self.focus(self._quest_book_win)

        elif key in KEYS_UP:
            if focused == self._spell_book_win:
                self.focus(self._char_sheet_win)
            elif focused == self._inventory_win:
                self.focus(self._equipment_win)
            elif focused == self._quest_book_win:
                self.focus(self._plot_win)

        elif key in KEYS_LEFT:
            if focused == self._equipment_win:
                self.focus(self._char_sheet_win)
            elif focused == self._inventory_win:
                self.focus(self._spell_book_win)
            elif focused == self._plot_win:
                self.focus(self._equipment_win)
            elif focused == self._quest_book_win:
                self.focus(self._inventory_win)

        elif key in KEYS_RIGHT:
            if focused == self._char_sheet_win:
                self.focus(self._equipment_win)
            elif focused == self._spell_book_win:
                self.focus(self._inventory_win)
            elif focused == self._equipment_win:
                self.focus(self._plot_win)
            elif focused == self._inventory_win:
                self.focus(self._quest_book_win)

        elif self._args.cheats and key == ord("t"):
            self._simulation.tick()

        elif self._args.cheats and key == ord("T"):
            for _ in range(100):
                self._simulation.tick()

        elif self._args.cheats and key == curses.ascii.DC4:  # ^t
            old = SignalMixin.emit
            SignalMixin.emit = lambda *_: None
            for _ in range(10000):
                self._simulation.tick()
            SignalMixin.emit = old
            for child in self._children:
                child.sync()

        else:
            super().keypress(key)

        curses.doupdate()

    def start(self) -> None:
        scr_height, scr_width = self.screen.getmaxyx()
        col1_width = int(scr_width * 0.3)
        col3_width = col1_width
        col2_width = scr_width - col1_width - col3_width

        self.screen.erase()
        self.screen.noutrefresh()

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

        self._focusable_children: T.List[Focusable] = [
            self._char_sheet_win,
            self._spell_book_win,
            self._equipment_win,
            self._inventory_win,
            self._plot_win,
            self._quest_book_win,
        ]
        self._children: T.List[Widget] = self._focusable_children + [
            self._task_win
        ]

    def stop(self) -> None:
        for child in self._children:
            child.stop()
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
        curses.doupdate()

    @property
    def focused(self) -> Focusable:
        for widget in self._focusable_children:
            if widget.focused:
                return widget
        raise AssertionError

    def focus(self, widget: Focusable) -> None:
        self.focused.focused = False
        widget.focused = True
