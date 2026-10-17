import functools
from collections.abc import Sequence
from typing import Any

from pqcli.config import Class
from pqcli.ui.curses.util import KEYS_CANCEL, Choice
from pqcli.ui.curses.views.menu_view import MenuView


class ChooseCharacterClassView(MenuView):
    def __init__(
        self,
        screen: Any,
        classes: Sequence[Class],
        class_: Class | None = None,
    ) -> None:
        super().__init__(
            screen,
            "Choose character class",
            classes.index(class_) if class_ is not None else 0,
        )

        for y, class_ in enumerate(classes, 1):
            key: str | None = str(y % 10) if y <= 10 else None
            self._choices.append(
                Choice(
                    keys=[ord(key)] if key is not None else [],
                    desc=f"[{key or '-'}] {class_.name}",
                    callback=functools.partial(self.on_confirm, class_),
                )
            )

        self._choices.append(
            Choice(
                keys=list(KEYS_CANCEL),
                desc="[Q] Cancel",
                callback=self.on_cancel,
            )
        )
