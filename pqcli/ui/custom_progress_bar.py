import urwid


class CustomProgressBar(urwid.ProgressBar):
    def __init__(self) -> None:
        super().__init__("progressbar-incomplete", "progressbar-done", 0, 1)

    def set_max(self, value: int) -> None:
        self._done = value
