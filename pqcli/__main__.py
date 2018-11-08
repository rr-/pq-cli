import argparse
from pathlib import Path

import xdg

from pqcli.roster import Roster
from pqcli.ui import Ui

SAVE_PATH = Path(xdg.XDG_CONFIG_HOME) / "pqcli" / "save.dat"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="pqcli")
    parser.add_argument(
        "--no-config",
        dest="use_config",
        action="store_false",
        help=(
            "Don't load or save configuration files from $XDG_CONFIG_HOME "
            "(player data will still be saved)"
        ),
    )
    parser.add_argument(
        "--no-save",
        dest="use_saves",
        action="store_false",
        help=argparse.SUPPRESS,
    )
    parser.add_argument("--cheats", action="store_true", help="???")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    roster = Roster.load(SAVE_PATH)

    try:
        Ui(roster, args).run()
    finally:
        if args.use_saves:
            roster.save()


if __name__ == "__main__":
    main()
