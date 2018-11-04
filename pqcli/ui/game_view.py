import datetime
import typing as T

import urwid

from pqcli.config import StatType
from pqcli.lingo import to_roman
from pqcli.mechanic import Player, Simulation, Spell
from pqcli.ui.custom_line_box import CustomLineBox
from pqcli.ui.custom_progress_bar import CustomProgressBar


class CharacterSheetView(CustomLineBox):
    def __init__(self, player: Player) -> None:
        self.player = player

        self.level_text = urwid.Text("")
        self.stat_texts = {stat: urwid.Text("") for stat in list(StatType)}

        self.list_box = urwid.ListBox(
            [
                urwid.Columns([urwid.Text("Name"), urwid.Text(player.name)]),
                urwid.Columns(
                    [urwid.Text("Race"), urwid.Text(player.race.name)]
                ),
                urwid.Columns(
                    [urwid.Text("Class"), urwid.Text(player.class_.name)]
                ),
                urwid.Columns([urwid.Text("Level"), self.level_text]),
                urwid.Divider(),
            ]
            + [
                urwid.Columns([urwid.Text(stat.value), self.stat_texts[stat]])
                for stat in StatType
            ]
        )

        self.player.connect("level_up", self.sync_level)
        self.player.stats.connect("change", self.sync_stats)
        self.sync_level()
        self.sync_stats()

        super().__init__(self.list_box, title="Character Sheet")

    def sync_level(self) -> None:
        self.level_text.set_text(str(self.player.level))

    def sync_stats(self) -> None:
        for stat in StatType:
            self.stat_texts[stat].set_text(str(self.player.stats[stat]))


class SpellBookView(CustomLineBox):
    def __init__(self, player: Player) -> None:
        self.player = player

        self.list_box = urwid.ListBox([])

        self.player.spell_book.connect("add", self.sync_spell_add)
        self.player.spell_book.connect("change", self.sync_spell_change)
        self.sync_spells()

        super().__init__(self.list_box, title="Spell Book")

    def sync_spells(self) -> None:
        del self.list_box.body[:]
        for spell in self.player.spell_book:
            self.sync_spell_add(spell)

    def sync_spell_add(self, spell: Spell) -> None:
        self.list_box.body.append(
            urwid.Columns(
                [urwid.Text(spell.name), urwid.Text(to_roman(spell.level))]
            )
        )

    def sync_spell_change(self, spell: Spell) -> None:
        for widget in self.list_box.body:
            if widget.contents[0][0].text == spell.name:
                widget.contents[1][0].set_text(to_roman(spell.level))


class TaskView(urwid.Pile):
    def __init__(self, player: Player) -> None:
        self.player = player

        self.current_task_text = urwid.Text("...")
        self.current_task_bar = CustomProgressBar()

        self.player.task_bar.connect("change", self.sync_position)
        self.player.connect("new_task", self.sync_task_name)
        self.sync_position()
        self.sync_task_name()

        super().__init__([self.current_task_text, self.current_task_bar])

    def sync_position(self) -> None:
        self.current_task_bar.set_completion(self.player.task_bar.position)
        self.current_task_bar.set_max(self.player.task_bar.max_)

    def sync_task_name(self) -> None:
        self.current_task_text.set_text(
            f"{self.player.task.description}..." if self.player.task else "?"
        )

    def pack(self, size: T.Tuple[int, int]) -> T.Tuple[int, int]:
        return (size[0], 2)


class GameView(urwid.Pile):
    signals = ["cancel"]

    def __init__(self, loop: urwid.MainLoop, player: Player) -> None:
        self.loop = loop
        self.player = player
        self.simulation = Simulation(player)
        self.last_tick = datetime.datetime.now()

        self.character_sheet_view = CharacterSheetView(player)
        self.spell_book_view = SpellBookView(player)
        self.task_view = TaskView(player)

        super().__init__(
            [
                urwid.Columns(
                    [
                        urwid.Pile(
                            [self.character_sheet_view, self.spell_book_view]
                        )
                    ]
                ),
                ("pack", self.task_view),
            ]
        )

        self.tick()

    def cancel(self) -> None:
        self._emit("cancel")

    def tick(self) -> None:
        now = datetime.datetime.now()
        elapsed = (now - self.last_tick).total_seconds()
        self.simulation.tick(elapsed * 1000)
        self.loop.set_alarm_in(0.1, lambda _loop, _user_data: self.tick())
        self.last_tick = datetime.datetime.now()

    def unhandled_input(self, key: str) -> bool:
        if key == "esc":
            self.cancel()
            return True

        return False
