import urwid


class MenuButton(urwid.Button):
    def __init__(self, label, *args, **kwargs):
        super().__init__("", *args, **kwargs)
        self._w = urwid.AttrMap(
            urwid.SelectableIcon(["\N{BULLET} ", label], 2),
            "button",
            "button-focus",
        )
