import typing as T

import urwid


class CustomLineBox(urwid.AttrMap):
    def __init__(
        self, widget: urwid.Widget, *args: T.Any, **kwargs: T.Any
    ) -> None:
        super().__init__(
            urwid.LineBox(
                urwid.AttrMap(widget, "linebox-content", "linebox-content"),
                *args,
                **kwargs,
            ),
            "linebox",
            "linebox-focus",
        )
