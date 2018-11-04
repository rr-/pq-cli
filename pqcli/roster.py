import pickle
import typing as T
from pathlib import Path

from pqcli.mechanic import Player


class Roster:
    def __init__(self) -> None:
        self.players: T.List[Player] = []

    def add_player(self, player: Player) -> None:
        self.players.append(player)

    @staticmethod
    def load(path: Path) -> "Roster":
        if path.exists():
            return pickle.loads(path.read_bytes())
        return Roster()

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(pickle.dumps(self))
