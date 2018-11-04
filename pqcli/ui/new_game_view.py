import random
import typing as T

import urwid
import urwid_readline

from pqcli.config import CLASSES, PRIME_STATS, RACES
from pqcli.mechanic import StatsBuilder, generate_name, create_player
from pqcli.ui.button import MenuButton
from pqcli.ui.line_box import LineBox


class StatsBox(LineBox):
    def __init__(self) -> None:
        self.stats_builder = StatsBuilder()
        self.stats = self.stats_builder.roll()
        self.stat_labels = {stat: urwid.Text("0") for stat in PRIME_STATS}
        self.total_label = urwid.Text("0")
        self.update_values()

        roll_button = MenuButton(
            "Roll", hint="F5", on_press=self.on_roll_press
        )
        unroll_button = MenuButton(
            "Unroll", hint="F6", on_press=self.on_unroll_press
        )

        value_texts = list(self.stat_labels.values())
        label_texts = [urwid.Text(f"{stat.value}: ") for stat in PRIME_STATS]

        super().__init__(
            urwid.ListBox(
                [
                    urwid.Columns(
                        [urwid.Pile(label_texts), urwid.Pile(value_texts)]
                    ),
                    urwid.Divider(),
                    urwid.Columns([urwid.Text("Total: "), self.total_label]),
                    urwid.Divider(),
                    roll_button,
                    unroll_button,
                ]
            ),
            title="Stats",
        )

    def roll(self) -> None:
        self.stats = self.stats_builder.roll()
        self.update_values()

    def unroll(self) -> None:
        try:
            self.stats = self.stats_builder.unroll()
        except IndexError:
            return
        self.update_values()

    def on_roll_press(self, _user_data: T.Any) -> None:
        self.roll()

    def on_unroll_press(self, _user_data: T.Any) -> None:
        self.unroll()

    def update_values(self) -> None:
        for stat, edit in self.stat_labels.items():
            edit.set_text(str(self.stats[stat]))
        self.total_label.set_text(
            str(sum(self.stats[stat] for stat in self.stat_labels.keys()))
        )


class RaceBox(LineBox):
    def __init__(self) -> None:
        self.race = random.choice(RACES)

        radio_buttons: T.List[urwid.RadioButton] = []
        for race in RACES:
            urwid.RadioButton(
                group=radio_buttons,
                label=race.name,
                state=race.name == self.race.name,
                on_state_change=self.on_state_change,
                user_data=race,
            )

        super().__init__(urwid.ListBox(radio_buttons), title="Race")

    def on_state_change(
        self, _widget: urwid.RadioButton, new_state: bool, user_data: T.Any
    ) -> None:
        if new_state:
            self.race = user_data


class ClassBox(LineBox):
    def __init__(self) -> None:
        self.class_ = random.choice(CLASSES)

        radio_buttons: T.List[urwid.RadioButton] = []
        for class_ in CLASSES:
            urwid.RadioButton(
                group=radio_buttons,
                label=class_.name,
                state=class_.name == self.class_.name,
                on_state_change=self.on_state_change,
                user_data=class_,
            )

        super().__init__(urwid.ListBox(radio_buttons), title="Class")

    def on_state_change(
        self, _widget: urwid.RadioButton, new_state: bool, user_data: T.Any
    ) -> None:
        if new_state:
            self.class_ = user_data


class NewGameView(urwid.Pile):
    signals = ["confirm", "cancel"]

    def __init__(self) -> None:
        self.race_box = RaceBox()
        self.class_box = ClassBox()
        self.stats_box = StatsBox()

        self.char_name_edit = urwid_readline.ReadlineEdit(
            "Name: ", generate_name()
        )
        generate_char_name_btn = MenuButton(
            "Generate random name",
            hint="F7",
            on_press=self.on_generate_char_name_press,
        )

        buttons_box = urwid.Filler(
            urwid.Padding(
                urwid.Pile(
                    [
                        MenuButton(
                            "Sold!", hint="F10", on_press=self.on_confirm_press
                        ),
                        MenuButton(
                            "Cancel", hint="Esc", on_press=self.on_cancel_press
                        ),
                    ]
                ),
                width=20,
                align="center",
            )
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
                        ("weight", 2, self.race_box),
                        ("weight", 2, self.class_box),
                        urwid.Pile([(13, self.stats_box), buttons_box]),
                    ]
                ),
            ]
        )

    def generate_random_char_name(self) -> None:
        self.char_name_edit.edit_text = generate_name()
        self.char_name_edit.edit_pos = len(self.char_name_edit.edit_text)

    def confirm(self) -> None:
        player = create_player(
            name=self.char_name_edit.edit_text,
            race=self.race_box.race,
            class_=self.class_box.class_,
            stats=self.stats_box.stats,
        )
        self._emit("confirm", player)

    def cancel(self) -> None:
        self._emit("cancel")

    def on_generate_char_name_press(self, _user_data: T.Any) -> None:
        self.generate_random_char_name()

    def on_confirm_press(self, _user_data: T.Any) -> None:
        self.confirm()

    def on_cancel_press(self, _user_data: T.Any) -> None:
        self.cancel()

    def unhandled_input(self, key: str) -> bool:
        if key == "esc":
            self.cancel()
            return True

        if key == "f7":
            self.generate_random_char_name()
            return True

        if key == "f5":
            self.stats_box.roll()
            return True

        if key == "f6":
            self.stats_box.unroll()
            return True

        if key == "f10":
            self.confirm()
            return True

        return False
