import datetime
import typing as T

import urwid


def format_float(num: float) -> str:
    ret = f"{num:.01f}"
    if ret.endswith("0"):
        ret = ret[:-2]
    return ret


def format_timespan(timespan: datetime.timedelta) -> str:
    num = timespan.total_seconds()
    if num < 60.0:
        return f"~{int(num)}s"
    num /= 60
    if num < 60.0:
        return f"~{int(num)}m"
    num /= 60
    if num < 24.0:
        return f"~{format_float(num)}h"
    num /= 24
    return f"~{format_float(num)}d"


class CustomProgressBar(urwid.Widget):
    _sizing = frozenset(["flow"])
    text_align = "center"
    eighths = " ▏▎▍▌▋▊▉"

    def __init__(self, show_time: bool) -> None:
        self.show_time = show_time
        self.position = 0.0
        self.max_ = 1.0
        self.normal = "progressbar-normal"
        self.complete = "progressbar-done"
        self.smooth = "progressbar-smooth"
        self.last_tick: T.Optional[datetime.datetime, float] = None

    @property
    def time_left(self) -> T.Optional[datetime.timedelta]:
        if self.last_tick is None:
            return None
        time_now = datetime.datetime.now()
        time_then = self.last_tick[0]
        pos_now = self.position
        pos_then = self.last_tick[1]
        speed = (pos_now - pos_then) / (time_now - time_then).total_seconds()
        if not speed:
            return None
        return datetime.timedelta(seconds=(self.max_ - pos_now) / speed)

    def set_completion(self, value: float) -> None:
        if self.last_tick is None or value == 0:
            self.last_tick = (datetime.datetime.now(), value)
        self.position = value
        self._invalidate()

    def set_max(self, value: T.Union[int, float]) -> None:
        if self.max_ == value:
            return
        self.last_tick = None
        self.max_ = value
        self._invalidate()

    def reset(self, cur: float, max_: T.Union[int, float]) -> None:
        if self.last_tick is None or cur == 0 or max_ != self.max_:
            self.last_tick = (datetime.datetime.now(), cur)
        self.position = cur
        self.max_ = max_
        self._invalidate()

    def rows(self, size: T.Tuple[int, int], focus: bool = False) -> int:
        return 1

    def get_text(self) -> str:
        percent = min(100.0, max(0.0, self.position * 100.0 / self.max_))
        ret = f"{percent:.02f}%"
        if self.time_left and self.show_time:
            ret += f" ({format_timespan(self.time_left)})"
        return ret

    # workaround for https://github.com/urwid/urwid/issues/317
    def render(self, size: T.Tuple[int, int], focus: bool = False) -> T.Any:
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
