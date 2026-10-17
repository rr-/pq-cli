import curses
import curses.ascii
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any, TypeVar, overload

KEYS_CYCLE = {curses.ascii.TAB}
KEYS_DOWN = set(map(ord, "jJ")) | {curses.KEY_DOWN}
KEYS_LEFT = set(map(ord, "hH")) | {curses.KEY_LEFT}
KEYS_RIGHT = set(map(ord, "lL")) | {curses.KEY_RIGHT}
KEYS_UP = set(map(ord, "kK")) | {curses.KEY_UP}
KEYS_CANCEL = set(map(ord, "qQ")) | {curses.ascii.ESC}


@dataclass
class Choice:
    keys: list[int]
    desc: str
    callback: Callable[..., Any]


ItemT = TypeVar("ItemT")
DefaultT = TypeVar("DefaultT")


@overload
def first(source: Iterable[ItemT]) -> ItemT | None: ...


@overload
def first(source: Iterable[ItemT], default: DefaultT) -> ItemT | DefaultT: ...


def first(source: Iterable[Any], default: Any = None) -> Any:
    return next(iter(source), default)
