import curses
import typing as T

from pqcli.ui.curses.widgets import (
    DataTable,
    ListBox,
    ProgressBar,
    WindowWrapper,
)


class ProgressBarWindow(WindowWrapper):
    def __init__(
        self, parent: T.Any, h: int, w: int, y: int, x: int, title: str
    ) -> None:
        super().__init__(parent, h, w, y, x)

        self._title = title

        try:
            self._progress_bar_win = (
                self._win.derwin(3, w, h - 3, 0) if self._win else None
            )
        except curses.error:
            self._progress_bar_win = None
        self._progress_bar = ProgressBar(
            self._progress_bar_win, 1, w - 2, 1, 1
        )

    def stop(self) -> None:
        super().stop()
        self._progress_bar.stop()

        del self._progress_bar_win
        self._progress_bar_win = None

    def _render_progress_bar(self, cur: float, max_: float, text: str) -> None:
        if not self._progress_bar_win:
            return

        self._progress_bar_win.erase()
        self._progress_bar_win.border(
            curses.ACS_VLINE,
            curses.ACS_VLINE,
            curses.ACS_HLINE,
            curses.ACS_HLINE,
            curses.ACS_LTEE,
            curses.ACS_RTEE,
            curses.ACS_LLCORNER,
            curses.ACS_LRCORNER,
        )

        x = max(0, (self.getmaxyx()[1] - len(text)) // 2)
        self._progress_bar_win.addnstr(
            0, x, text, min(len(text), self._progress_bar_win.getmaxyx()[1])
        )
        self._progress_bar.set_position(cur, max_)
        self._progress_bar_win.refresh()


class DataTableProgressBarWindow(ProgressBarWindow):
    def __init__(
        self,
        parent: T.Any,
        h: int,
        w: int,
        y: int,
        x: int,
        title: str,
        align_right: bool,
    ) -> None:
        super().__init__(parent, h, w, y, x, title)

        self._data_table = DataTable(
            self._win, h - 4, w - 2, 1, 1, align_right
        )

    def stop(self) -> None:
        super().stop()
        self._data_table.stop()

    def _render_data_table(self) -> None:
        if not self._win:
            return

        self._win.box()
        x = max(0, (self.getmaxyx()[1] - len(self._title)) // 2)
        self._win.addnstr(
            0, x, self._title, min(len(self._title), self.getmaxyx()[1])
        )
        self._win.refresh()
        self._data_table.render()


class ListBoxProgressBarWindow(ProgressBarWindow):
    def __init__(
        self, parent: T.Any, h: int, w: int, y: int, x: int, title: str
    ) -> None:
        super().__init__(parent, h, w, y, x, title)

        self._list_box = ListBox(self._win, h - 4, w - 2, 1, 1)

    def stop(self) -> None:
        super().stop()
        self._list_box.stop()

    def _render_list_box(self) -> None:
        if not self._win:
            return

        self._win.box()
        x = max(0, (self.getmaxyx()[1] - len(self._title)) // 2)
        self._win.addnstr(
            0, x, self._title, min(len(self._title), self.getmaxyx()[1])
        )
        self._win.refresh()
        self._list_box.render()
