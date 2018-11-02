import typing as T

import urwid


class LineBox(urwid.AttrWrap):
    def __init__(
        self, widget: urwid.Widget, *args: T.Any, **kwargs: T.Any
    ) -> None:
        super().__init__(
            urwid.LineBox(
                urwid.AttrWrap(widget, "linebox-content", "linebox-content"),
                *args,
                **kwargs,
            ),
            "linebox",
            "linebox-focus",
        ),
