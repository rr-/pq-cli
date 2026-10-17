from typing import Any


class BaseView:
    def __init__(self, screen: Any) -> None:
        self.screen = screen

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def idle(self) -> None:
        pass

    def keypress(self, key: int) -> None:
        pass
