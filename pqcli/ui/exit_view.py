import typing as T

import urwid

from pqcli.game_state import Roster


class ExitView(urwid.Overlay):
    def __init__(
        self, parent: urwid.Widget, on_exit: T.Callable, on_cancel: T.Callable
    ) -> None:
        self.on_exit = on_exit
        self.on_cancel = on_cancel

        question = urwid.Text(("bold", "Really quit?"), "center")
        yes_btn = urwid.Button("Yes", lambda _user_data: self.on_exit())
        no_btn = urwid.Button("No", lambda _user_data: self.on_cancel())

        line_box = urwid.LineBox(
            urwid.ListBox(
                urwid.SimpleFocusListWalker([question, no_btn, yes_btn])
            )
        )

        super().__init__(line_box, parent, "center", 20, "middle", 5)

    def keypress(self, size: T.Any, key: str) -> bool:
        if key in {"y", "Y"}:
            self.on_exit()
            return True
        if key in {"n", "N"}:
            self.on_cancel()
            return True
        return super().keypress(size, key)
