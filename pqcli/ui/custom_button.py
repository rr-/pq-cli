import typing as T

import urwid

_MAGIC = 999  # where to display the cursor (high value = don't display it)


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
                    (urwid.PACK, urwid.Text("< ")),
                    urwid.SelectableIcon([label], _MAGIC),
                    (
                        urwid.PACK,
                        urwid.Text(f"[{hint}]" if hint else "", align="right"),
                    ),
                    (urwid.PACK, urwid.Text(" >")),
                ]
            ),
            "button",
            "button-focus",
        )
