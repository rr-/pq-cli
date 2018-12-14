import typing as T
from dataclasses import dataclass


@dataclass
class Choice:
    keys: T.List[int]
    desc: str
    callback: T.Callable[..., T.Any]


def first(source: T.Iterable[T.Any], default: T.Any = None) -> T.Any:
    return next(iter(source), default)
