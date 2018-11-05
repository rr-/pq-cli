import pickle
import typing as T
from pathlib import Path

from pqcli.mechanic import Player


class Roster:
    def __init__(self, path: Path, players: T.List[Player]) -> None:
        self.path = path
        self.players = players

    @staticmethod
    def load(path: T.Union[str, Path]) -> "Roster":
        real_path = Path(path)
        if real_path.exists():
            return Roster(
                real_path, players=pickle.loads(real_path.read_bytes())
            )
        return Roster(real_path, players=[])

    def save(self) -> None:
        old_path = self.path.with_name(self.path.name + ".old")
        tmp_path = self.path.with_name(self.path.name + ".new")
        tmp_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path.write_bytes(pickle.dumps(self.players))
        if self.path.exists():
            self.path.rename(old_path)
        tmp_path.rename(self.path)
