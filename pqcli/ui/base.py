import abc
import argparse
import typing as T

from pqcli.mechanic import Player
from pqcli.roster import Roster


class BaseUserInterface(abc.ABC):
    def __init__(
        self,
        roster: Roster,
        player: T.Optional[Player],
        args: argparse.Namespace,
    ) -> None:
        self.roster = roster
        self.args = args
        self.player = player

    @abc.abstractmethod
    def run(self) -> None:
        raise NotImplementedError("not implemented")
