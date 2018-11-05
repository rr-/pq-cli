import urwid


class ReadOnlyCheckBox(urwid.Text):
    def __init__(self, text: str, state: bool = False) -> None:
        self.icons = {
            key: widget.text for key, widget in urwid.CheckBox.states.items()
        }
        self._caption = text

        super().__init__("")

        self.set_state(state)

    def set_state(self, state: bool) -> None:
        self.set_text(self.icons[state] + " " + self._caption)
