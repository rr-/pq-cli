import curses
import typing as T

from .base import WindowWrapper


class Scrollable(WindowWrapper):
    def __init__(self, *args: T.Any, **kwargs: T.Any) -> None:
        super().__init__(*args, **kwargs)
        self._scroll_y = 0
        self._pad: T.Optional[T.Any] = curses.newpad(1, 1)
        self._items: T.List[T.Any] = []

    def clear(self) -> None:
        self._items = []
        self.scroll_to_item(0)

    def scroll_to_item(self, y: int) -> None:
        if not self._items or not self._win:
            return
        if y < 0:
            y %= len(self._items)
        while not (self._scroll_y <= y < self._scroll_y + self.getmaxyx()[0]):
            self._scroll_y += 1 if self._scroll_y < y else -1

    def stop(self) -> None:
        super().stop()
        del self._pad
        self._pad = None

    def __len__(self) -> int:
        return len(self._items)

    def render(self) -> None:
        if not self._pad:
            return

        if self._items:
            self._pad.resize(
                max(1, len(self._items)), max(1, self.getmaxyx()[1] + 1)
            )
        else:
            self._pad.resize(1, 1)

        self._pad.erase()
        try:
            self._render_impl()
        except curses.error:
            pass

    def _render_impl(self) -> None:
        raise NotImplementedError("not implemented")
