import typing as T

import urwid

from pqcli.ui.button import MenuButton


class ExitView(urwid.Overlay):
    signals = ["exit", "cancel"]

    def __init__(self, parent: urwid.Widget) -> None:
        question = urwid.Text(("bold", "Really quit?"), "center")
        yes_btn = MenuButton("Yes", lambda _user_data: self.exit())
        no_btn = MenuButton("No", lambda _user_data: self.cancel())

        line_box = urwid.LineBox(
            urwid.ListBox(
                urwid.SimpleFocusListWalker([question, no_btn, yes_btn])
            )
        )

        super().__init__(line_box, parent, "center", 20, "middle", 5)

    def keypress(self, size: T.Any, key: str) -> T.Optional[str]:
        if key in {"y", "Y"}:
            self.exit()
            return None
        if key in {"n", "N"}:
            self.cancel()
            return None
        return T.cast(T.Optional[str], super().keypress(size, key))

    def exit(self) -> None:
        self._emit("exit")

    def cancel(self) -> None:
        self._emit("cancel")
