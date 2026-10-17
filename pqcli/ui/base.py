import abc
import argparse

from pqcli.game_data import GameData
from pqcli.mechanic import Player
from pqcli.roster import Roster


class BaseUserInterface(abc.ABC):
    def __init__(
        self,
        roster: Roster,
        player: Player | None,
        args: argparse.Namespace,
        data: GameData,
    ) -> None:
        self.roster = roster
        self.data = data
        self.args = args
        self.player = player

    @abc.abstractmethod
    def run(self) -> None:
        raise NotImplementedError("not implemented")
