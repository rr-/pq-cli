import typing as T

import urwid

# workaround for https://github.com/urwid/urwid/issues/317


class CustomProgressBar(urwid.Widget):
    _sizing = frozenset(["flow"])
    text_align = "center"
    eighths = u" ▏▎▍▌▋▊▉"

    def __init__(self) -> None:
        self.position = 0.0
        self.max_ = 1.0
        self.normal = "progressbar-normal"
        self.complete = "progressbar-done"
        self.smooth = "progressbar-smooth"

    def set_completion(self, value: float) -> None:
        self.position = value
        self._invalidate()

    def set_max(self, value: T.Union[int, float]) -> None:
        self.max_ = value
        self._invalidate()

    def rows(self, size: T.Tuple[int, int], focus: bool = False) -> int:
        return 1

    def get_text(self) -> str:
        percent = min(100, max(0, int(self.position * 100 / self.max_)))
        return str(percent) + " %"

    def render(self, size: T.Tuple[int, int], focus: bool = False) -> None:
        (maxcol,) = size
        txt = urwid.Text(self.get_text(), self.text_align, "clip")
        c = txt.render((maxcol,))
        t = c._text[0]

        cf = self.position * maxcol / self.max_
        ccol_dirty = int(cf)
        ccol = len(
            c._text[0][:ccol_dirty].decode("utf-8", "ignore").encode("utf-8")
        )

        cs = 0
        cs = int((cf - ccol) * 8)

        if ccol < 0 or (ccol == 0 and cs == 0):
            c._attr = [[(self.normal, maxcol)]]
        elif ccol >= maxcol:
            c._attr = [[(self.complete, maxcol)]]
        elif cs and c._text[0][ccol] == 32:
            t = c._text[0]
            cenc = self.eighths[cs].encode("utf-8")
            c._text[0] = t[:ccol] + cenc + t[ccol + 1 :]
            a = []
            if ccol > 0:
                a.append((self.complete, ccol))
            a.append((self.smooth, len(cenc)))
            if maxcol - ccol - 1 > 0:
                a.append((self.normal, maxcol - ccol - 1))
            c._attr = [a]
            c._cs = [[(None, len(c._text[0]))]]
        else:
            c._attr = [[(self.complete, ccol), (self.normal, maxcol - ccol)]]
        return c
