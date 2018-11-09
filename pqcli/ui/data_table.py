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

        self.resize_columns()
        self._rows.append(widgets)

    def delete_row(self, idx: int) -> None:
        del self.contents[idx]
        del self._rows[idx]
        self.resize_columns()

    def delete_rows(self, start_idx: int, end_idx: int) -> None:
        del self.contents[start_idx:end_idx]
        del self._rows[start_idx:end_idx]
        self.resize_columns()

    def resize_columns(self) -> None:
        if not self._rows:
            return

        for i, sizing in enumerate(self._columns):
            if isinstance(sizing, tuple) and sizing[0] == urwid.PACK:
                width = max(
                    row_widgets[i].pack()[0] for row_widgets in self._rows
                )
                for item in self.contents:
                    columns = item[0]
                    columns.contents[i] = (
                        columns.contents[i][0],
                        (urwid.GIVEN, width, None),
                    )
