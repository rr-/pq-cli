import curses
import typing as T
from dataclasses import dataclass

KEYS_DOWN = set(map(ord, "jJ")) | {curses.KEY_DOWN}
KEYS_LEFT = set(map(ord, "hH")) | {curses.KEY_LEFT}
KEYS_RIGHT = set(map(ord, "lL")) | {curses.KEY_RIGHT}
KEYS_UP = set(map(ord, "kK")) | {curses.KEY_UP}


@dataclass
class Choice:
    keys: T.List[int]
    desc: str
    callback: T.Callable[..., T.Any]


def first(source: T.Iterable[T.Any], default: T.Any = None) -> T.Any:
    return next(iter(source), default)
