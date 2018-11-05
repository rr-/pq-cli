import typing as T

import urwid


class CustomButton(urwid.Button):
    def __init__(
        self,
        label: str,
        *args: T.Any,
        hint: T.Optional[str] = None,
        **kwargs: T.Any,
    ) -> None:
        super().__init__("", *args, **kwargs)
        self._w = urwid.AttrMap(
            urwid.Columns(
                [
                    ("pack", urwid.Text("< ")),
                    urwid.SelectableIcon([label], 0),
                    (
                        "pack",
                        urwid.Text(f"[{hint}]" if hint else "", align="right"),
                    ),
                    ("pack", urwid.Text(" >")),
                ]
            ),
            "button",
            "button-focus",
        )