import typing as T

import urwid


class CustomListWalker(urwid.SimpleFocusListWalker):
    def append(self, item) -> None:
        super().append(item)
        self.set_focus(len(self) - 1)


class CustomListBox(urwid.ListBox):
    def __init__(self, widgets: T.List[urwid.Widget]) -> None:
        super().__init__(CustomListWalker(widgets))
