import curses

from pqcli.ui.curses.colors import COLOR_HIGHLIGHT, has_colors

from .scrollable import Scrollable


class ListBox(Scrollable[str]):
    def __init__(
        self, parent: curses.window | None, h: int, w: int, y: int, x: int
    ) -> None:
        super().__init__(parent, h, w, y, x)
        self._selected: int | None = None

    def add(self, text: str) -> None:
        self._items.append(text)
        self.scroll_to_item(-1)

    def set(self, idx: int, value: str) -> None:
        if idx < 0:
            idx %= len(self._items)
        self._items[idx] = value

    def get(self, idx: int) -> str | None:
        if not self._items:
            return None
        if idx < 0:
            idx %= len(self._items)
        try:
            return self._items[idx]
        except IndexError:
            return None

    def delete(self, idx: int, count: int = 1) -> None:
        del self._items[idx : idx + count]

    def select(self, idx: int | None) -> None:
        if idx is not None and idx < 0 and self._items:
            idx %= len(self._items)
        self._selected = idx

    def _render_impl(self, h: int, w: int) -> None:
        assert self._pad
        for y, item in enumerate(self._items):
            if y == self._selected and has_colors():
                self._pad.attron(curses.color_pair(COLOR_HIGHLIGHT))
            self._pad.addnstr(y, 0, item, min(len(item), w))
            if y == self._selected and has_colors():
                self._pad.attroff(curses.color_pair(COLOR_HIGHLIGHT))
