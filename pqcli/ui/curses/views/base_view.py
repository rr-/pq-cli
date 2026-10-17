import curses


class BaseView:
    def __init__(self, screen: curses.window) -> None:
        self.screen = screen

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def idle(self) -> None:
        pass

    def keypress(self, key: int) -> None:
        pass
