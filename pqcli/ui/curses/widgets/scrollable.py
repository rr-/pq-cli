import curses
import typing as T

from pqcli.ui.curses.colors import (
    COLOR_SCROLLBAR_THUMB,
    COLOR_SCROLLBAR_TRACK,
    has_colors,
)

from .base import WindowWrapper


class Scrollable(WindowWrapper):
    def __init__(self, parent: T.Any, h: int, w: int, y: int, x: int) -> None:
        super().__init__(parent, h, w, y, x)
        self._scroll_pos = 0
        self._pad: T.Optional[T.Any] = curses.newpad(1, 1)
        self._items: T.List[T.Any] = []

    def clear(self) -> None:
        self._items = []
        self.scroll_to_item(0)

    def scroll_page_up(self) -> None:
        self.scroll_to_item(max(0, self._scroll_pos - self.getmaxyx()[0]))

    def scroll_page_down(self) -> None:
        self.scroll_to_item(
            min(
                len(self._items) - 1,
                self._scroll_pos + self.getmaxyx()[0] * 2 - 1,
            )
        )

    def scroll_to_item(self, y: int) -> None:
        if not self._items or not self._win:
            return
        if y < 0:
            y %= len(self._items)

        h = self.getmaxyx()[0]
        delta = 1 if self._scroll_pos < y else -1
        while not self._scroll_pos <= y < self._scroll_pos + h:
            self._scroll_pos += delta

    def stop(self) -> None:
        super().stop()
        del self._pad
        self._pad = None

    def __len__(self) -> int:
        return len(self._items)

    def render(self) -> None:
        if not self._pad or not self._win:
            return

        if self._items:
            self._pad.resize(
                max(1, len(self._items)), max(1, self.getmaxyx()[1] + 1)
            )
        else:
            self._pad.resize(1, 1)

        self._win.erase()
        self._win.noutrefresh()

        self._pad.erase()
        h, w = self.getmaxyx()
        y, x = self.getbegyx()

        try:
            if self._scroll_pos > 0 or self._scroll_pos + h < len(self._items):
                y1 = self._scroll_pos
                y2 = self._scroll_pos + h
                thumb_y1 = int(y1 * h // len(self._items))
                thumb_y2 = int(y2 * h // len(self._items))

                attr_thumb = (
                    curses.color_pair(COLOR_SCROLLBAR_THUMB)
                    if has_colors()
                    else curses.A_REVERSE
                )
                attr_track = (
                    curses.color_pair(COLOR_SCROLLBAR_TRACK)
                    if has_colors()
                    else curses.A_NORMAL
                )

                for win_y in range(h):
                    self._win.chgat(
                        win_y,
                        w - 1,
                        attr_thumb
                        if thumb_y1 <= win_y <= thumb_y2
                        else attr_track,
                    )
                self._win.noutrefresh()

                self._render_impl(h, w - 1)
                self._pad.noutrefresh(
                    self._scroll_pos, 0, y, x, y + h - 1, x + w - 2
                )
            else:
                self._render_impl(h, w)
                self._pad.noutrefresh(
                    self._scroll_pos, 0, y, x, y + h - 1, x + w - 1
                )

        except curses.error:
            pass

    def _render_impl(self, h: int, w: int) -> None:
        raise NotImplementedError("not implemented")
