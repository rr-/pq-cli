import typing as T

from ..event_handler import EventHandler
from .base_view import BaseView


class CreateCharacterView(BaseView):
    def __init__(self, screen: T.Any) -> None:
        super().__init__(screen)

        self.on_cancel = EventHandler()
        self.on_confirm = EventHandler()

    def keypress(self, key: int) -> None:
        if key in map(ord, "qQ\N{ESC}"):
            self.on_cancel()
