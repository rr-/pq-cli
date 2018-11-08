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
from pqcli.ui.custom_list_box import CustomListBox
from pqcli.ui.custom_progress_bar import CustomProgressBar
from pqcli.ui.double_line_box import DoubleLineBox
from pqcli.ui.read_only_check_box import ReadOnlyCheckBox
from pqcli.ui.scrollable import ScrollBar, Scrollable


class CharacterSheetView(DoubleLineBox):
    def __init__(self, player: Player) -> None:
        self.player = player

        self.level_text = urwid.Text("")
        self.stat_texts = {stat: urwid.Text("") for stat in list(StatType)}
        self.exp_bar = CustomProgressBar()

        self.list_box = CustomListBox(
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
        self.player.exp_bar.connect("change", self.sync_exp)

        super().__init__(
            top_widget=self.list_box,
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
        self.exp_bar.set_completion(cur)
        self.exp_bar.set_max(max_)
        self.set_bottom_title(f"Experience ({max_-cur:.0f} XP to go)")


class SpellBookView(CustomLineBox):
    def __init__(self, player: Player) -> None:
        self.player = player

        self.list_box = CustomListBox([])

        self.player.spell_book.connect("add", self.sync_spell_add)
        self.player.spell_book.connect("change", self.sync_spell_change)

        super().__init__(self.list_box, title="Spell Book")
        self.sync()

    def sync(self) -> None:
        del self.list_box.body[:]
        for spell in self.player.spell_book:
            self.sync_spell_add(spell)

    def sync_spell_add(self, spell: Spell) -> None:
        self.list_box.body.append(
            urwid.Columns(
                [
                    ("weight", 3, urwid.Text(spell.name)),
                    urwid.Text(to_roman(spell.level)),
                ]
            )
        )

    def sync_spell_change(self, spell: Spell) -> None:
        for widget in self.list_box.body:
            if widget.contents[0][0].text == spell.name:
                widget.contents[1][0].set_text(to_roman(spell.level))


class EquipmentView(CustomLineBox):
    def __init__(self, player: Player) -> None:
        self.player = player

        self.value_texts = {
            equipment_type: urwid.Text("") for equipment_type in EquipmentType
        }
        self.list_box = CustomListBox(
            [
                urwid.Columns(
                    [
                        urwid.Text(equipment_type.value),
                        ("weight", 3, self.value_texts[equipment_type]),
                    ]
                )
                for equipment_type in EquipmentType
            ]
        )

        self.player.equipment.connect("change", self.sync_equipment_change)

        super().__init__(self.list_box, title="Equipment")
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

        self.gold_text = urwid.Text("")
        self.pile = urwid.Pile(
            [
                urwid.Columns(
                    [("weight", 3, urwid.Text("Gold")), self.gold_text]
                )
            ]
        )
        self.scrollable = Scrollable(self.pile)
        self.encumbrance_bar = CustomProgressBar()

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
        del self.pile.contents[1:]
        for item in self.player.inventory:
            self.sync_item_add(item)

    def sync_encumbrance_position(self) -> None:
        cur = self.player.inventory.encum_bar.position
        max_ = self.player.inventory.encum_bar.max_
        self.encumbrance_bar.set_completion(cur)
        self.encumbrance_bar.set_max(max_)
        self.set_bottom_title(f"Encumbrance ({cur:.0f}/{max_} cubits)")

    def sync_item_add(self, item: InventoryItem) -> None:
        self.pile.contents.append(
            (
                urwid.Columns(
                    [
                        ("weight", 3, urwid.Text(item.name)),
                        urwid.Text(str(item.quantity)),
                    ]
                ),
                ("pack", None),
            )
        )
        self.scrollable.set_scrollpos(self.scrollable.rows_max() - 1)

    def sync_item_del(self, item: InventoryItem) -> None:
        idx = self.get_item_idx_by_name(item.name)
        if idx is not None:
            del self.pile.contents[idx]

    def sync_item_change(self, item: InventoryItem) -> None:
        idx = self.get_item_idx_by_name(item.name)
        if idx is not None:
            column_widget = self.pile.contents[idx][0]
            column_widget.contents[1][0].set_text(str(item.quantity))

    def get_item_idx_by_name(self, name: str) -> T.Optional[int]:
        for i, pile_item in enumerate(self.pile.contents):
            if pile_item[0].contents[0][0].text == name:
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

        self.list_box = CustomListBox([])
        self.plot_bar = CustomProgressBar()

        self.player.quest_book.connect("complete_act", self.sync_act_add)
        self.player.quest_book.plot_bar.connect("change", self.sync_position)

        super().__init__(
            top_widget=self.list_box,
            top_title="Plot Development",
            bottom_widget=self.plot_bar,
        )
        self.sync()

    def sync(self) -> None:
        self.sync_acts()
        self.sync_position()

    def sync_acts(self) -> None:
        del self.list_box.body[:]
        for act_number in range(
            max(0, self.player.quest_book.act - self.cutoff),
            self.player.quest_book.act,
        ):
            self.list_box.body.append(
                ReadOnlyCheckBox(act_name(act_number), state=True)
            )
        self.list_box.body.append(
            ReadOnlyCheckBox(act_name(self.player.quest_book.act), state=False)
        )

    def sync_act_add(self) -> None:
        del self.list_box.body[: -self.cutoff]
        if self.list_box.body:
            self.list_box.body[-1].set_state(True)
        self.list_box.body.append(
            ReadOnlyCheckBox(act_name(self.player.quest_book.act), state=False)
        )

    def sync_position(self) -> None:
        self.plot_bar.set_completion(self.player.quest_book.plot_bar.position)
        self.plot_bar.set_max(self.player.quest_book.plot_bar.max_)


class QuestBookView(DoubleLineBox):
    cutoff = 100

    def __init__(self, player: Player) -> None:
        self.player = player

        self.pile = urwid.Pile([])
        self.quest_bar = CustomProgressBar()
        self.scrollable = Scrollable(self.pile)

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
        del self.pile.contents[: -self.cutoff]
        if self.pile.contents:
            self.pile.contents[-1][0].set_state(True)
        self.pile.contents.append(
            (ReadOnlyCheckBox(quest_name, state=False), ("pack", None))
        )
        self.scrollable.set_scrollpos(self.scrollable.rows_max() - 1)

    def sync_position(self) -> None:
        self.quest_bar.set_completion(
            self.player.quest_book.quest_bar.position
        )
        self.quest_bar.set_max(self.player.quest_book.quest_bar.max_)


class TaskView(urwid.Pile):
    def __init__(self, player: Player) -> None:
        self.player = player

        self.current_task_text = urwid.Text("...")
        self.current_task_bar = CustomProgressBar()

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
        self.current_task_bar.set_completion(self.player.task_bar.position)
        self.current_task_bar.set_max(self.player.task_bar.max_)

    def pack(self, size: T.Tuple[int, int]) -> T.Tuple[int, int]:
        return (size[0], 2)


class GameView(urwid.Pile):
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

        super().__init__(
            [
                urwid.Columns(
                    [
                        (
                            "weight",
                            1,
                            urwid.Pile(
                                [
                                    (19, self.character_sheet_view),
                                    self.spell_book_view,
                                ]
                            ),
                        ),
                        (
                            "weight",
                            2,
                            urwid.Pile(
                                [
                                    (15, self.equipment_view),
                                    self.inventory_view,
                                ]
                            ),
                        ),
                        (
                            "weight",
                            2,
                            urwid.Pile(
                                [(15, self.plot_view), self.quest_book_view]
                            ),
                        ),
                    ]
                ),
                ("pack", self.task_view),
            ]
        )

    def cancel(self) -> None:
        self._emit("cancel")

    def tick(self) -> None:
        now = datetime.datetime.now()
        elapsed = (now - self.last_tick).total_seconds()
        self.simulation.tick(elapsed * 1000)
        self.last_tick = datetime.datetime.now()

    def unhandled_input(self, key: str) -> bool:
        if key == "esc":
            self.cancel()
            return True

        if self.args.cheats:
            if key == "e":
                self.simulation.player.exp_bar.increment(1)
                return True

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

                return True

        return False

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
