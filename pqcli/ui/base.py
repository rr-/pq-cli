import abc
import argparse

from pqcli.roster import Roster


class BaseUserInterface(abc.ABC):
    def __init__(self, roster: Roster, args: argparse.Namespace) -> None:
        self.roster = roster
        self.args = args

    @abc.abstractmethod
    def run(self) -> None:
        raise NotImplementedError("not implemented")
