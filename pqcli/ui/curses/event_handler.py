from collections.abc import Callable
from typing import Generic, ParamSpec

P = ParamSpec("P")


class EventHandler(Generic[P]):
    def __init__(self) -> None:
        self.callbacks: list[Callable[P, object]] = []

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> None:
        for callback in self.callbacks:
            callback(*args, **kwargs)

    def __iadd__(self, callback: Callable[P, object]) -> "EventHandler[P]":
        self.callbacks.append(callback)
        return self
