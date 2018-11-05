import datetime
import typing as T

import urwid

from pqcli.config import EquipmentType, StatType
from pqcli.lingo import act_name, to_roman
from pqcli.mechanic import InventoryItem, Player, Simulation, Spell
from pqcli.ui.custom_line_box import CustomLineBox
from pqcli.ui.custom_progress_bar import CustomProgressBar
from pqcli.ui.read_only_check_box import ReadOnlyCheckBox


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


class ExperienceView(urwid.Pile):
    def __init__(self, player: Player) -> None:
        self.player = player

        self.exp_bar = CustomProgressBar()

        self.player.exp_bar.connect("change", self.sync_position)
        self.sync_position()

        super().__init__([urwid.Text("Experience"), self.exp_bar])

    def sync_position(self) -> None:
        self.exp_bar.set_completion(self.player.exp_bar.position)
        self.exp_bar.set_max(self.player.exp_bar.max_)

    def pack(self, size: T.Tuple[int, int]) -> T.Tuple[int, int]:
        return (size[0], 2)


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


class EquipmentView(CustomLineBox):
    def __init__(self, player: Player) -> None:
        self.player = player

        self.value_texts = {
            equipment_type: urwid.Text("") for equipment_type in EquipmentType
        }
        self.list_box = urwid.ListBox(
            [
                urwid.Columns(
                    [
                        urwid.Text(equipment_type.value),
                        self.value_texts[equipment_type],
                    ]
                )
                for equipment_type in EquipmentType
            ]
        )

        self.player.equipment.connect("change", self.sync_equipment_change)
        self.sync_equipment()

        super().__init__(self.list_box, title="Equipment")

    def sync_equipment(self) -> None:
        for equipment_type in EquipmentType:
            self.sync_equipment_change(
                equipment_type, self.player.equipment[equipment_type]
            )

    def sync_equipment_change(
        self, equipment_type: EquipmentType, item_name: str
    ) -> None:
        self.value_texts[equipment_type].set_text(item_name or "")


class InventoryView(urwid.Pile):
    def __init__(self, player: Player) -> None:
        self.player = player

        self.gold_text = urwid.Text("")
        self.list_box = urwid.ListBox(
            [urwid.Columns([urwid.Text("Gold"), self.gold_text])]
        )
        self.encumbrance_bar = CustomProgressBar()

        self.player.inventory.connect("gold_change", self.sync_gold)
        self.player.inventory.connect("item_add", self.sync_item_add)
        self.player.inventory.connect("item_del", self.sync_item_del)
        self.player.inventory.connect("item_change", self.sync_item_change)
        self.player.inventory.encum_bar.connect(
            "change", self.sync_encumbrance_position
        )
        self.sync_gold()
        self.sync_items()
        self.sync_encumbrance_position()

        super().__init__(
            [
                CustomLineBox(self.list_box, title="Inventory"),
                (1, urwid.Filler(urwid.Text("Encumbrance"))),
                (1, urwid.Filler(self.encumbrance_bar)),
            ]
        )

    def sync_gold(self) -> None:
        self.gold_text.set_text(str(self.player.inventory.gold))

    def sync_items(self) -> None:
        del self.list_box.body[1:]
        for item in self.player.inventory:
            self.sync_item_add(item)

    def sync_encumbrance_position(self) -> None:
        self.encumbrance_bar.set_completion(
            self.player.inventory.encum_bar.position
        )
        self.encumbrance_bar.set_max(self.player.inventory.encum_bar.max_)

    def sync_item_add(self, item: InventoryItem) -> None:
        self.list_box.body.append(
            urwid.Columns(
                [urwid.Text(item.name), urwid.Text(str(item.quantity))]
            )
        )

    def sync_item_del(self, item: InventoryItem) -> None:
        idx = self.get_item_idx_by_name(item.name)
        if idx is not None:
            del self.list_box.body[idx]

    def sync_item_change(self, item: InventoryItem) -> None:
        idx = self.get_item_idx_by_name(item.name)
        if idx is not None:
            self.list_box.body[idx].contents[1][0].set_text(str(item.quantity))

    def get_item_idx_by_name(self, name: str) -> T.Optional[int]:
        for i, column_widget in enumerate(self.list_box.body):
            if column_widget.contents[0][0].text == name:
                return i
        return None


class PlotView(urwid.Pile):
    cutoff = 100

    def __init__(self, player: Player) -> None:
        self.player = player

        self.list_box = urwid.ListBox([])
        self.plot_bar = CustomProgressBar()

        self.player.connect("complete_act", self.sync_act_add)
        self.player.plot_bar.connect("change", self.sync_position)
        self.sync_acts()
        self.sync_position()

        super().__init__(
            [
                CustomLineBox(self.list_box, title="Plot Development"),
                (1, urwid.Filler(self.plot_bar)),
            ]
        )

    def sync_acts(self) -> None:
        del self.list_box.body[:]
        for act_number in range(
            max(0, self.player.act - self.cutoff), self.player.act
        ):
            self.list_box.body.append(
                ReadOnlyCheckBox(act_name(act_number), state=True)
            )
        self.list_box.body.append(
            ReadOnlyCheckBox(act_name(self.player.act), state=False)
        )

    def sync_act_add(self):
        del self.list_box.body[: -self.cutoff]
        if self.list_box.body:
            self.list_box.body[-1].set_state(True)
        self.list_box.body.append(
            ReadOnlyCheckBox(act_name(self.player.act), state=False)
        )
        self.list_box.set_focus(len(self.list_box.body) - 1)

    def sync_position(self) -> None:
        self.plot_bar.set_completion(self.player.plot_bar.position)
        self.plot_bar.set_max(self.player.plot_bar.max_)


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
        self.experience_view = ExperienceView(player)
        self.spell_book_view = SpellBookView(player)
        self.equipment_view = EquipmentView(player)
        self.inventory_view = InventoryView(player)
        self.plot_view = PlotView(player)
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
                                    self.character_sheet_view,
                                    ("pack", self.experience_view),
                                    self.spell_book_view,
                                ]
                            ),
                        ),
                        (
                            "weight",
                            2,
                            urwid.Pile(
                                [self.equipment_view, self.inventory_view]
                            ),
                        ),
                        ("weight", 2, urwid.Pile([self.plot_view])),
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
