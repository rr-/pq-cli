import curses
import enum
import typing as T

from .scrollable import Scrollable


class ListBox(Scrollable):
    _items: T.List[str]

    def add(self, text: str) -> None:
        self._items.append(text)
        self.scroll_to_item(-1)

    def set(self, idx: int, value: str) -> None:
        if idx < 0:
            idx %= len(self._items)
        self._items[idx] = value

    def get(self, idx: int) -> T.Optional[str]:
        if not self._items:
            return None
        if idx < 0:
            idx %= len(self._items)
        try:
            return self._items[idx]
        except ValueError:
            return None

    def delete(self, idx: int, count: int = 1) -> None:
        del self._items[idx : idx + count]

    def _render_impl(self) -> None:
        assert self._pad
        h, w = self.getmaxyx()
        for y, item in enumerate(self._items):
            self._pad.addnstr(y, 0, item, min(len(item), w))

        y, x = self.getbegyx()
        self._pad.refresh(self._scroll_y, 0, y, x, y + h - 1, x + w - 1)
