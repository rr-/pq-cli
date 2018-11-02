import random
import typing as T

import urwid
import urwid_readline

from pqcli.game_state import Player, StatsBuilder, generate_name, create_player
from pqcli.config import RACES, CLASSES, PRIME_STATS
from pqcli.ui.button import MenuButton
from pqcli.ui.line_box import LineBox


class StatsBox(urwid.Filler):
    def __init__(self, player: Player, stats_builder: StatsBuilder) -> None:
        self.player = player
        self.stats_builder = stats_builder
        self.stat_labels = {stat: urwid.Text("0") for stat in PRIME_STATS}
        self.total_label = urwid.Text("0")
        self.update_values()

        roll_button = MenuButton("Roll", on_press=self.on_roll_press)
        unroll_button = MenuButton("Unroll", on_press=self.on_unroll_press)

        value_texts = list(self.stat_labels.values())
        label_texts = [urwid.Text(f"{stat.value}: ") for stat in PRIME_STATS]

        super().__init__(
            urwid.Pile(
                [
                    (
                        13,
                        LineBox(
                            urwid.ListBox(
                                [
                                    urwid.Columns(
                                        [
                                            urwid.Pile(label_texts),
                                            urwid.Pile(value_texts),
                                        ]
                                    ),
                                    urwid.Divider(),
                                    urwid.Columns(
                                        [
                                            urwid.Text("Total: "),
                                            self.total_label,
                                        ]
                                    ),
                                    urwid.Divider(),
                                    roll_button,
                                    unroll_button,
                                ]
                            ),
                            title="Stats",
                        ),
                    )
                ]
            ),
            valign="top",
        )

    def on_roll_press(self, _user_data: T.Any) -> None:
        self.player.stats = self.stats_builder.roll()
        self.update_values()

    def on_unroll_press(self, _user_data: T.Any) -> None:
        try:
            self.player.stats = self.stats_builder.unroll()
        except IndexError:
            return
        self.update_values()

    def update_values(self) -> None:
        for stat, edit in self.stat_labels.items():
            edit.set_text(str(self.player.stats[stat]))
        self.total_label.set_text(
            str(
                sum(
                    self.player.stats[stat] for stat in self.stat_labels.keys()
                )
            )
        )


class RaceBox(LineBox):
    def __init__(self, player: Player) -> None:
        race_checkboxes = []
        for race in RACES:
            urwid.RadioButton(
                group=race_checkboxes,
                label=race.name,
                state=race.name == player.race.name,
            )
        super().__init__(urwid.ListBox(race_checkboxes), title="Race")


class ClassBox(LineBox):
    def __init__(self, player: Player) -> None:
        class_checkboxes = []
        for class_ in CLASSES:
            urwid.RadioButton(
                group=class_checkboxes,
                label=class_.name,
                state=class_.name == player.class_.name,
            )
        super().__init__(urwid.ListBox(class_checkboxes), title="Class")


class NewGameView(urwid.Pile):
    def __init__(self, on_confirm: T.Callable, on_cancel: T.Callable) -> None:
        self.on_confirm = on_confirm
        self.on_cancel = on_cancel

        stats_builder = StatsBuilder()
        self.player = create_player(stats_builder)

        race_box = RaceBox(self.player)
        class_box = ClassBox(self.player)
        stats_box = StatsBox(self.player, stats_builder)

        self.char_name_edit = urwid_readline.ReadlineEdit(
            "Name: ", self.player.name
        )
        generate_char_name_btn = MenuButton(
            "Generate random name", on_press=self.on_generate_char_name_press
        )

        urwid.connect_signal(
            self.char_name_edit, "postchange", self.on_char_name_change
        )

        super().__init__(
            [
                (1, urwid.Filler(self.char_name_edit)),
                (
                    1,
                    urwid.Filler(
                        urwid.Padding(
                            generate_char_name_btn,
                            left=len(self.char_name_edit.caption),
                        )
                    ),
                ),
                urwid.Columns(
                    [
                        ("weight", 2, race_box),
                        ("weight", 2, class_box),
                        stats_box,
                    ]
                ),
            ]
        )

    def generate_random_char_name(self) -> None:
        self.char_name_edit.edit_text = generate_name()
        self.char_name_edit.edit_pos = len(self.char_name_edit.edit_text)

    def on_char_name_change(self, widget: urwid.Text, old_text: str) -> None:
        self.player.name = widget.edit_text

    def on_generate_char_name_press(self, _user_data: T.Any) -> None:
        self.generate_random_char_name()

    def unhandled_input(self, key: str) -> bool:
        if key == "esc":
            self.on_cancel()
            return True

        return False
