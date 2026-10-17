from collections.abc import Callable
from typing import Any


class EventHandler:
    def __init__(self) -> None:
        self.callbacks: list[Callable[..., Any]] = []

    def __call__(self, *args: Any, **kwargs: Any) -> None:
        for callback in self.callbacks:
            callback(*args, **kwargs)

    def __iadd__(self, callback: Callable[..., Any]) -> "EventHandler":
        self.callbacks.append(callback)
        return self
