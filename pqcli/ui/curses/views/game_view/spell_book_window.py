import typing as T

from pqcli.lingo import to_roman
from pqcli.mechanic import Player, Spell
from pqcli.ui.curses.widgets import DataTable, WindowWrapper


class SpellBookWindow(WindowWrapper):
    def __init__(
        self, player: Player, parent: T.Any, h: int, w: int, y: int, x: int
    ) -> None:
        super().__init__(parent, h, w, y, x)

        self._data_table = DataTable(
            self._win, h - 2, w - 2, 1, 1, align_right=True
        )

        self._player = player
        self._player.spell_book.connect("add", self._sync_spell_add)
        self._player.spell_book.connect("change", self._sync_spell_change)

        self._sync()

    def stop(self) -> None:
        super().stop()
        self._data_table.stop()

        self._player.spell_book.disconnect("add", self._sync_spell_add)
        self._player.spell_book.disconnect("change", self._sync_spell_change)

    def _sync(self) -> None:
        self._data_table.clear()
        for spell in self._player.spell_book:
            self._data_table.add(spell.name, to_roman(spell.level))
        self._render()

    def _sync_spell_add(self, spell: Spell) -> None:
        self._data_table.add(spell.name, to_roman(spell.level))
        self._render()

    def _sync_spell_change(self, spell: Spell) -> None:
        self._data_table.set(spell.name, to_roman(spell.level))
        self._render()

    def _render(self) -> None:
        if not self._win:
            return

        self._win.box()
        text = " Spell Book "
        x = max(0, (self.getmaxyx()[1] - len(text)) // 2)
        self._win.addnstr(0, x, text, min(len(text), self.getmaxyx()[1]))
        self._win.refresh()
        self._data_table.render()
