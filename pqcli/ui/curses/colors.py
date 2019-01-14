_HAS_COLORS = False

COLOR_LOGO = 1
COLOR_LOGO_ALT = 2
COLOR_FOCUSED = 3
COLOR_SCROLLBAR_TRACK = 4
COLOR_SCROLLBAR_THUMB = 5
COLOR_PROGRESSBAR = 6
COLOR_HIGHLIGHT = 7


def has_colors() -> bool:
    return _HAS_COLORS


def set_colors(has_colors: bool) -> None:
    global _HAS_COLORS
    _HAS_COLORS = has_colors
