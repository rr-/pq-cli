import argparse
import contextlib
import datetime
import typing as T

import urwid

from pqcli.config import EquipmentType, StatType
from pqcli.lingo import act_name, to_roman
from pqcli.mechanic import (
    InventoryItem,
    Player,
    SignalMixin,
    Simulation,
    Spell,
)
from pqcli.ui.custom_line_box import CustomLineBox
from pqcli.ui.custom_progress_bar import CustomProgressBar
from pqcli.ui.data_table import DataTable
from pqcli.ui.double_line_box import DoubleLineBox
from pqcli.ui.layout import NColumns, NPile
from pqcli.ui.read_only_check_box import ReadOnlyCheckBox
from pqcli.ui.scrollable import Scrollable, ScrollBar


class CharacterSheetView(DoubleLineBox):
    def __init__(self, player: Player) -> None:
        self.player = player

        self.level_text = urwid.Text("")
        self.stat_texts = {stat: urwid.Text("") for stat in list(StatType)}
        self.exp_bar = CustomProgressBar(show_time=True)

        data_table = DataTable(columns=[(urwid.WEIGHT, 1), (urwid.WEIGHT, 2)])
        data_table.add_row(urwid.Text("Name"), urwid.Text(player.name))
        data_table.add_row(urwid.Text("Race"), urwid.Text(player.race.name))
        data_table.add_row(urwid.Text("Class"), urwid.Text(player.class_.name))
        data_table.add_row(urwid.Text("Level"), self.level_text)
        data_table.add_row(urwid.Divider(), urwid.Divider())
        for stat in StatType:
            data_table.add_row(urwid.Text(stat.value), self.stat_texts[stat])

        self.player.connect("level_up", self.sync_level)
        self.player.stats.connect("change", self.sync_stats)
        self.player.exp_bar.connect("change", self.sync_exp)

        super().__init__(
            top_widget=ScrollBar(Scrollable(data_table)),
            bottom_widget=self.exp_bar,
            top_title="Character Sheet",
            bottom_title="Experience",
        )
        self.sync()

    def sync(self) -> None:
        self.sync_level()
        self.sync_stats()
        self.sync_exp()

    def sync_level(self) -> None:
        self.level_text.set_text(str(self.player.level))

    def sync_stats(self) -> None:
        for stat in StatType:
            self.stat_texts[stat].set_text(str(self.player.stats[stat]))

    def sync_exp(self) -> None:
        cur = self.player.exp_bar.position
        max_ = self.player.exp_bar.max_
        self.exp_bar.reset(cur, max_)
        self.set_bottom_title(f"Experience ({max_-cur:.0f} XP to go)")


class SpellBookView(CustomLineBox):
    def __init__(self, player: Player) -> None:
        self.player = player

        self.data_table = DataTable(columns=[(urwid.WEIGHT, 3), (urwid.PACK,)])
        self.scrollable = Scrollable(self.data_table)

        self.player.spell_book.connect("add", self.sync_spell_add)
        self.player.spell_book.connect("change", self.sync_spell_change)

        super().__init__(ScrollBar(self.scrollable), title="Spell Book")
        self.sync()

    def sync(self) -> None:
        self.data_table.delete_rows(0, len(self.data_table.data_rows))
        for spell in self.player.spell_book:
            self.sync_spell_add(spell)

    def sync_spell_add(self, spell: Spell) -> None:
        self.data_table.add_row(
            urwid.Text(spell.name), urwid.Text(to_roman(spell.level))
        )
        self.scrollable.set_scrollpos(len(self.data_table.data_rows) - 1)

    def sync_spell_change(self, spell: Spell) -> None:
        for row_widgets in self.data_table.data_rows:
            if row_widgets[0].text == spell.name:
                row_widgets[1].set_text(to_roman(spell.level))
        self.data_table.resize_columns()


class EquipmentView(CustomLineBox):
    def __init__(self, player: Player) -> None:
        self.player = player

        self.value_texts = {
            equipment_type: urwid.Text("") for equipment_type in EquipmentType
        }
        data_table = DataTable(columns=[(urwid.WEIGHT, 1), (urwid.WEIGHT, 3)])
        for equipment_type in EquipmentType:
            data_table.add_row(
                urwid.Text(equipment_type.value),
                self.value_texts[equipment_type],
            )

        self.player.equipment.connect("change", self.sync_equipment_change)

        super().__init__(ScrollBar(Scrollable(data_table)), title="Equipment")
        self.sync()

    def sync(self) -> None:
        for equipment_type in EquipmentType:
            self.sync_equipment_change(
                equipment_type, self.player.equipment[equipment_type]
            )

    def sync_equipment_change(
        self, equipment_type: EquipmentType, item_name: T.Optional[str]
    ) -> None:
        self.value_texts[equipment_type].set_text(item_name or "")


class InventoryView(DoubleLineBox):
    def __init__(self, player: Player) -> None:
        self.player = player

        self.gold_text = urwid.Text("", align=urwid.RIGHT)
        self.data_table = DataTable(columns=[(urwid.WEIGHT, 3), (urwid.PACK,)])
        self.data_table.add_row(urwid.Text("Gold"), self.gold_text)
        self.scrollable = Scrollable(self.data_table)
        self.encumbrance_bar = CustomProgressBar(show_time=False)

        self.player.connect("new_task", self.on_new_task)
        self.player.inventory.connect("gold_change", self.sync_gold)
        self.player.inventory.connect("item_add", self.sync_item_add)
        self.player.inventory.connect("item_del", self.sync_item_del)
        self.player.inventory.connect("item_change", self.sync_item_change)
        self.player.inventory.encum_bar.connect(
            "change", self.sync_encumbrance_position
        )

        super().__init__(
            top_widget=ScrollBar(self.scrollable),
            top_title="Inventory",
            bottom_widget=self.encumbrance_bar,
            bottom_title="Encumbrance",
        )
        self.sync()

    def sync(self) -> None:
        self.sync_gold()
        self.sync_items()
        self.sync_encumbrance_position()

    def sync_gold(self) -> None:
        self.gold_text.set_text(str(self.player.inventory.gold))

    def sync_items(self) -> None:
        self.data_table.delete_rows(1, len(self.data_table.data_rows) - 1)
        for item in self.player.inventory:
            self.sync_item_add(item)

    def sync_encumbrance_position(self) -> None:
        cur = self.player.inventory.encum_bar.position
        max_ = self.player.inventory.encum_bar.max_
        self.encumbrance_bar.reset(cur, max_)
        self.set_bottom_title(f"Encumbrance ({cur:.0f}/{max_} cubits)")

    def sync_item_add(self, item: InventoryItem) -> None:
        self.data_table.add_row(
            urwid.Text(item.name),
            urwid.Text(str(item.quantity), align=urwid.RIGHT),
        )
        self.scrollable.set_scrollpos(self.scrollable.rows_max() - 1)

    def sync_item_del(self, item: InventoryItem) -> None:
        idx = self.get_item_idx_by_name(item.name)
        if idx is not None:
            self.data_table.delete_row(idx)

    def sync_item_change(self, item: InventoryItem) -> None:
        idx = self.get_item_idx_by_name(item.name)
        if idx is not None:
            self.data_table.data_rows[idx][1].set_text(str(item.quantity))

    def get_item_idx_by_name(self, name: str) -> T.Optional[int]:
        for i, row_widgets in enumerate(self.data_table.data_rows):
            if row_widgets[0].text == name:
                return i
        return None

    def on_new_task(self) -> None:
        description = self.player.task.description if self.player.task else "?"
        if description.lower().startswith("sell"):
            self.scrollable.set_scrollpos(0)


class PlotView(DoubleLineBox):
    cutoff = 100

    def __init__(self, player: Player) -> None:
        self.player = player

        self.data_table = DataTable(columns=[(urwid.WEIGHT, 1)])
        self.scrollable = Scrollable(self.data_table)
        self.plot_bar = CustomProgressBar(show_time=True)

        self.player.quest_book.connect("start_act", self.sync_act_add)
        self.player.quest_book.plot_bar.connect("change", self.sync_position)

        super().__init__(
            top_widget=ScrollBar(self.scrollable),
            top_title="Plot Development",
            bottom_widget=self.plot_bar,
        )
        self.sync()

    def sync(self) -> None:
        self.sync_acts()
        self.sync_position()

    def sync_acts(self) -> None:
        self.data_table.delete_rows(0, len(self.data_table.data_rows))
        for act_number in range(
            max(0, self.player.quest_book.act - self.cutoff),
            self.player.quest_book.act + 1,
        ):
            self.sync_act_add(act_number)

    def sync_act_add(self, act_number: int) -> None:
        self.data_table.delete_rows(
            0, max(0, self.data_table.row_count - self.cutoff)
        )
        if self.data_table.data_rows:
            self.data_table.data_rows[-1][0].set_state(True)
        self.data_table.add_row(
            ReadOnlyCheckBox(act_name(act_number), state=False)
        )
        self.scrollable.set_scrollpos(self.scrollable.rows_max() - 1)

    def sync_position(self) -> None:
        self.plot_bar.reset(
            self.player.quest_book.plot_bar.position,
            self.player.quest_book.plot_bar.max_,
        )


class QuestBookView(DoubleLineBox):
    cutoff = 100

    def __init__(self, player: Player) -> None:
        self.player = player

        self.data_table = DataTable(columns=[(urwid.WEIGHT, 1)])
        self.quest_bar = CustomProgressBar(show_time=True)
        self.scrollable = Scrollable(self.data_table)

        self.player.quest_book.connect("start_quest", self.sync_quest_add)
        self.player.quest_book.quest_bar.connect("change", self.sync_position)

        super().__init__(
            top_widget=ScrollBar(self.scrollable),
            top_title="Quests",
            bottom_widget=self.quest_bar,
        )
        self.sync()

    def sync(self) -> None:
        self.sync_quests()
        self.sync_position()

    def sync_quests(self) -> None:
        for quest_name in self.player.quest_book.quests[-self.cutoff :]:
            self.sync_quest_add(quest_name)

    def sync_quest_add(self, quest_name: str) -> None:
        self.data_table.delete_rows(
            0, max(0, self.data_table.row_count - self.cutoff)
        )
        if self.data_table.data_rows:
            self.data_table.data_rows[-1][0].set_state(True)
        self.data_table.add_row(ReadOnlyCheckBox(quest_name, state=False))
        self.scrollable.set_scrollpos(self.scrollable.rows_max() - 1)

    def sync_position(self) -> None:
        self.quest_bar.reset(
            self.player.quest_book.quest_bar.position,
            self.player.quest_book.quest_bar.max_,
        )


class TaskView(NPile):
    def __init__(self, player: Player) -> None:
        self.player = player

        self.current_task_text = urwid.Text("...")
        self.current_task_bar = CustomProgressBar(show_time=False)

        self.player.connect("new_task", self.sync_task_name)
        self.player.task_bar.connect("change", self.sync_position)

        super().__init__([self.current_task_text, self.current_task_bar])
        self.sync()

    def sync(self) -> None:
        self.sync_task_name()
        self.sync_position()

    def sync_task_name(self) -> None:
        self.current_task_text.set_text(
            f"{self.player.task.description}..." if self.player.task else "?"
        )

    def sync_position(self) -> None:
        self.current_task_bar.reset(
            self.player.task_bar.position, self.player.task_bar.max_
        )

    def pack(self, size: T.Tuple[int, int]) -> T.Tuple[int, int]:
        return (size[0], 2)


class GameView(NPile):
    signals = ["cancel"]

    def __init__(
        self, loop: urwid.MainLoop, player: Player, args: argparse.Namespace
    ) -> None:
        self.loop = loop
        self.player = player
        self.args = args
        self.simulation = Simulation(player)
        self.last_tick = datetime.datetime.now()

        self.character_sheet_view = CharacterSheetView(player)
        self.spell_book_view = SpellBookView(player)
        self.equipment_view = EquipmentView(player)
        self.inventory_view = InventoryView(player)
        self.plot_view = PlotView(player)
        self.quest_book_view = QuestBookView(player)
        self.task_view = TaskView(player)

        self.columns = NColumns(
            [
                (
                    urwid.WEIGHT,
                    4,
                    NPile(
                        [(19, self.character_sheet_view), self.spell_book_view]
                    ),
                ),
                (
                    urwid.WEIGHT,
                    5,
                    NPile([(15, self.equipment_view), self.inventory_view]),
                ),
                (
                    urwid.WEIGHT,
                    4,
                    NPile([(15, self.plot_view), self.quest_book_view]),
                ),
            ]
        )

        super().__init__(
            [self.columns, (urwid.PACK, self.task_view)], outermost=True
        )

    def cancel(self) -> None:
        self._emit("cancel")

    def tick(self) -> None:
        now = datetime.datetime.now()
        elapsed = (now - self.last_tick).total_seconds()
        self.simulation.tick(elapsed * 1000)
        self.last_tick = datetime.datetime.now()

    def keypress(self, size: T.Tuple[int, int], key: str) -> bool:
        if key == "esc":
            self.cancel()
            return None

        if self._command_map[key] == urwid.CURSOR_RIGHT:
            old_focus_position = self.columns.focus.focus_position
            self.columns.focus_position = min(
                self.columns.focus_position + 1, len(self.columns.contents) - 1
            )
            self.columns.focus.focus_position = old_focus_position
            return None

        if self._command_map[key] == urwid.CURSOR_LEFT:
            old_focus_position = self.columns.focus.focus_position
            self.columns.focus_position = max(
                self.columns.focus_position - 1, 0
            )
            self.columns.focus.focus_position = old_focus_position
            return None

        if self.args.cheats:
            if key == "e":
                self.simulation.player.exp_bar.increment(1)
                return None

            fast_forward = {"t": 1, "T": 100, "ctrl t": 10000}
            if key in fast_forward:
                iterations = fast_forward[key]
                ctx_mgr = (
                    self.suppress_updates()
                    if iterations >= 1000
                    else contextlib.suppress()
                )

                with ctx_mgr:
                    for _ in range(iterations):
                        self.simulation.tick()

                return None

        return super().keypress(size, key)

    @contextlib.contextmanager
    def suppress_updates(self) -> T.Generator:
        old = SignalMixin.emit
        SignalMixin.emit = lambda *_: None
        yield
        self.character_sheet_view.sync()
        self.spell_book_view.sync()
        self.equipment_view.sync()
        self.inventory_view.sync()
        self.plot_view.sync()
        self.quest_book_view.sync()
        self.task_view.sync()
        SignalMixin.emit = old
