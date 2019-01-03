from .base import WindowWrapper


class Label(WindowWrapper):
    def set_text(self, text: str) -> None:
        if not self._win:
            return
        self._win.erase()
        self._win.addnstr(text, min(len(text), self.getmaxyx()[1] - 1))
        self._win.noutrefresh()
