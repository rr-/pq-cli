import typing as T


class EventHandler:
    def __init__(self) -> None:
        self.callbacks: T.List[T.Callable[..., T.Any]] = []

    def __call__(self, *args: T.Any, **kwargs: T.Any) -> None:
        for callback in self.callbacks:
            callback(*args, **kwargs)

    def __iadd__(self, callback: T.Callable[..., T.Any]) -> "EventHandler":
        self.callbacks.append(callback)
        return self
