import argparse
from pathlib import Path

import xdg

from pqcli.roster import Roster
from pqcli.ui import Ui

SAVE_PATH = Path(xdg.XDG_CONFIG_HOME) / "pqcli" / "save.dat"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="pqcli")
    parser.add_argument("--cheats", help="enable cheats", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    roster = Roster.load(SAVE_PATH)

    try:
        Ui(roster, args).run()
    finally:
        roster.save(SAVE_PATH)


if __name__ == "__main__":
    main()
