import typing as T

import urwid


class MenuButton(urwid.Button):
    def __init__(
        self,
        label: str,
        *args: T.Any,
        hint: T.Optional[str] = None,
        **kwargs: T.Any
    ) -> None:
        super().__init__("", *args, **kwargs)
        self._w = urwid.AttrMap(
            urwid.Columns(
                [
                    urwid.SelectableIcon(["\N{BULLET} ", label], 2),
                    ("pack", urwid.Text(hint or "", align="right")),
                ]
            ),
            "button",
            "button-focus",
        )
