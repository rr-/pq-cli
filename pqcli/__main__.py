import argparse
import sys
import typing as T
from pathlib import Path

from xdg_base_dirs import xdg_config_home

from pqcli.game_data import (
    DataError,
    GameData,
    dump_builtin_data,
    load_game_data,
)
from pqcli.mechanic import Player
from pqcli.roster import Roster
from pqcli.ui.basic import BasicUserInterface
from pqcli.ui.curses import CursesUserInterface

SAVE_PATH = Path(xdg_config_home()) / "pqcli" / "save.dat"
DATA_PATH = Path(xdg_config_home()) / "pqcli" / "data"


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
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DATA_PATH,
        metavar="DIR",
        help=(
            "directory with custom word lists; each NAME.json replaces "
            f"the built-in list of that name (default: {DATA_PATH})"
        ),
    )
    parser.add_argument(
        "--dump-data",
        type=Path,
        metavar="DIR",
        help="copy the built-in word lists to DIR for editing and exit",
    )
    return parser.parse_args()


def list_players(roster: Roster, file: T.Optional[T.Any] = None) -> None:
    for i, player in enumerate(roster.players, start=1):
        print(f"{i}. {player.name}", file=file)


def bootstrap_first_run(
    roster: Roster, args: argparse.Namespace, data: GameData
) -> None:
    if roster.players or args.list_saves or args.load_save:
        return

    print("No saved characters found. Starting first-run character creation.")
    ui = BasicUserInterface(roster, None, args, data)
    while not roster.players:
        player = ui.create_player(auto_play=False)
        if player:
            return
        if not ui.confirm("No character created. Do you want to try again?"):
            print("A character is required for first run.", file=sys.stderr)
            raise SystemExit(1)


def main() -> None:
    args = parse_args()

    if args.dump_data:
        try:
            paths = dump_builtin_data(args.dump_data)
        except DataError as ex:
            print(f"pqcli: {ex}", file=sys.stderr)
            exit(1)
        print(f"Wrote {len(paths)} files to {args.dump_data}")
        exit(0)

    try:
        data = load_game_data(args.data_dir)
    except DataError as ex:
        print(f"pqcli: {ex}", file=sys.stderr)
        exit(1)

    roster = Roster.load(SAVE_PATH)

    if args.list_saves:
        list_players(roster)
        exit(0)

    player: T.Optional[Player] = None
    if args.load_save:
        try:
            player = list(roster.players)[args.load_save - 1]
        except IndexError:
            print("Invalid player. Available players:", file=sys.stderr)
            list_players(roster, file=sys.stderr)
            exit(1)

    bootstrap_first_run(roster, args, data)

    try:
        ui = args.ui(roster, player, args, data)
        ui.run()
    finally:
        if args.use_saves:
            roster.save()


if __name__ == "__main__":
    main()
