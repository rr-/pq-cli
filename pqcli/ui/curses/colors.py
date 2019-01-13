_HAS_COLORS = False

COLOR_LOGO = 1
COLOR_FOCUSED = 2
COLOR_SCROLLBAR_TRACK = 3
COLOR_SCROLLBAR_THUMB = 4
COLOR_PROGRESSBAR = 5


def has_colors() -> bool:
    return _HAS_COLORS


def set_colors(has_colors: bool) -> None:
    global _HAS_COLORS
    _HAS_COLORS = has_colors
