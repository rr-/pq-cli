from pathlib import Path

import xdg

from pqcli.roster import Roster
from pqcli.ui import Ui

SAVE_PATH = Path(xdg.XDG_CONFIG_HOME) / "pqcli" / "save.dat"


def main() -> None:
    roster = Roster.load(SAVE_PATH)

    try:
        Ui(roster).run()
    finally:
        roster.save(SAVE_PATH)


if __name__ == "__main__":
    main()
