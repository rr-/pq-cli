import argparse
import sys
import typing as T
from pathlib import Path

from xdg_base_dirs import xdg_config_home

from pqcli.mechanic import Player
from pqcli.roster import Roster
from pqcli.ui.basic import BasicUserInterface
from pqcli.ui.curses import CursesUserInterface

SAVE_PATH = Path(xdg_config_home()) / "pqcli" / "save.dat"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="pqcli")

    group = parser.add_mutually_exclusive_group()
    group.set_defaults(ui=CursesUserInterface)
    group.add_argument(
        "--basic",
        dest="ui",
        action="store_const",
        const=BasicUserInterface,
        help="Use basic user interface (very crude, but uses least CPU)",
    )
    group.add_argument(
        "--curses",
        dest="ui",
        action="store_const",
        const=CursesUserInterface,
        help="Use curses user interface (fast, but no colors output)",
    )

    parser.add_argument(
        "--no-colors",
        dest="colors",
        action="store_false",
        help="Disable color highlighting in curses interface",
    )

    parser.add_argument(
        "--no-save",
        dest="use_saves",
        action="store_false",
        help=argparse.SUPPRESS,
    )
    parser.add_argument("--cheats", action="store_true", help="???")
    parser.add_argument(
        "--list-saves",
        action="store_true",
        help="list saved characters and exit",
    )
    parser.add_argument(
        "--load-save",
        type=int,
        metavar="NUM",
        help="play chosen character",
    )
    return parser.parse_args()


def list_players(roster: Roster, file: T.Optional[T.Any] = None) -> None:
    for i, player in enumerate(roster.players, start=1):
        print(f"{i}. {player.name}", file=file)


def main() -> None:
    args = parse_args()
    roster = Roster.load(SAVE_PATH)

    if args.list_saves:
        list_players(roster)
        exit(0)

    player: T.Optional[Player] = None
    if args.load_save:
        try:
            player = list(roster.players)[args.load_save - 1]
        except IndexError:
            print(f"Invalid player. Available players:", file=sys.stderr)
            list_players(roster, file=sys.stderr)
            exit(1)

    try:
        ui = args.ui(roster, player, args)
        ui.run()
    finally:
        if args.use_saves:
            roster.save()


if __name__ == "__main__":
    main()
