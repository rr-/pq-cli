import urwid

from pqcli.ui.layout import NPile


class DoubleLineBox(urwid.AttrMap):
    def __init__(
        self,
        top_widget: urwid.Widget,
        bottom_widget: urwid.Widget,
        top_title: str = "",
        bottom_title: str = "",
    ) -> None:
        self.top_line_box = urwid.LineBox(
            urwid.AttrMap(top_widget, "linebox-content", "linebox-content"),
            title=top_title,
            bline="",
        )

        self.bottom_line_box = urwid.LineBox(
            urwid.AttrMap(bottom_widget, "linebox-content", "linebox-content"),
            title=bottom_title,
            tlcorner="├",
            trcorner="┤",
        )

        super().__init__(
            NPile([self.top_line_box, (urwid.PACK, self.bottom_line_box)]),
            "linebox",
            "linebox-focus",
        )

    def set_bottom_title(self, text: str) -> None:
        self.bottom_line_box.set_title(text)
