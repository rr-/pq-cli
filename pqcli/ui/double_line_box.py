import typing as T

import urwid


class DoubleLineBox(urwid.AttrWrap):
    def __init__(
        self,
        top_widget: urwid.Widget,
        bottom_widget: urwid.Widget,
        top_title: str = "",
        bottom_title: str = "",
    ) -> None:
        super().__init__(
            urwid.Pile(
                [
                    urwid.LineBox(
                        urwid.AttrWrap(
                            top_widget, "linebox-content", "linebox-content"
                        ),
                        title=top_title,
                        bline="",
                    ),
                    (
                        "pack",
                        urwid.LineBox(
                            urwid.AttrWrap(
                                bottom_widget,
                                "linebox-content",
                                "linebox-content",
                            ),
                            title=bottom_title,
                            tlcorner="├",
                            trcorner="┤",
                        ),
                    ),
                ]
            ),
            "linebox",
            "linebox-focus",
        )
