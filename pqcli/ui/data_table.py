import typing as T

import urwid

from pqcli.ui.layout import NColumns, NPile


class DataTable(NPile):
    def __init__(self, columns: T.Any) -> None:
        self.column_count = len(columns)
        self._columns = columns
        self._rows: T.List[T.List[urwid.Widget]] = []
        super().__init__([])

    @property
    def row_count(self) -> int:
        return len(self._rows)

    @property
    def data_rows(self) -> T.Iterable[T.List[urwid.Widget]]:
        # "rows" was already used by urwid
        return self._rows

    def add_row(self, *widgets: T.List[urwid.Widget]) -> None:
        if len(widgets) != self.column_count:
            raise VauleError(f"Expected {self.column_count} widgets")

        self.contents.append(
            (
                NColumns(
                    list((*x, y) for x, y in zip(self._columns, widgets))
                ),
                (urwid.PACK, 1),
            )
        )
        self._rows.append(widgets)

    def delete_row(self, idx: int) -> None:
        del self.contents[idx]
        del self._rows[idx]

    def delete_rows(self, start_idx: int, end_idx: int) -> None:
        del self.contents[start_idx:end_idx]
        del self._rows[start_idx:end_idx]
