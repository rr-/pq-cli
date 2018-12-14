import curses
import enum
import typing as T

from .scrollable import Scrollable


class DataTable(Scrollable):
    def __init__(
        self,
        parent: T.Any,
        h: int,
        w: int,
        y: int,
        x: int,
        align_right: bool = False,
    ) -> None:
        super().__init__(parent, h, w, y, x)

        self._align_right = align_right
        self._items: T.List[T.Tuple[str, str]]

    def add(self, text: str, value: str) -> None:
        self._items.append((text, value))
        self.scroll_to_item(-1)

    def set(self, text: str, value: str) -> None:
        idx = self.get_idx(text)
        if idx is None:
            self.add(text, value)
        else:
            self._items[idx] = (self._items[idx][0], value)
            self.scroll_to_item(idx)

    def delete(self, text: str) -> None:
        idx = self.get_idx(text)
        if idx is not None:
            del self._items[idx]
            self.scroll_to_item(idx)

    def get_idx(self, text: str) -> T.Optional[int]:
        for idx, row in enumerate(self._items):
            if row[0].strip() == text.strip():
                return idx
        return None

    def _render_impl(self) -> None:
        assert self._pad
        h, w = self.getmaxyx()
        if self._align_right:
            for y, row in enumerate(self._items):
                self._pad.move(y, 0)
                self._pad.addnstr(row[0], min(len(row[0]), w))
                col2_x = max(0, w - len(row[1]))
                if col2_x < w:
                    self._pad.move(y, col2_x)
                    self._pad.addstr(row[1])
        else:
            col2_x = self._get_col_width(0)
            for y, row in enumerate(self._items):
                self._pad.addnstr(y, 0, row[0], min(len(row[0]), w))
                if col2_x < w:
                    self._pad.addnstr(
                        y, col2_x, row[1], min(len(row[1]), w - col2_x)
                    )

        y, x = self.getbegyx()
        self._pad.refresh(self._scroll_y, 0, y, x, y + h - 1, x + w - 1)

    def _get_col_width(self, x: int) -> int:
        return max([len(row[0]) for row in self._items] + [0])
