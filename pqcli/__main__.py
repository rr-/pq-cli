import pickle
from pathlib import Path

import xdg

from pqcli.game_state import Roster
from pqcli.ui import Ui


SAVE_PATH = Path(xdg.XDG_CONFIG_HOME) / "pqcli" / "save.dat"


def main() -> None:
    if SAVE_PATH.exists():
        roster = pickle.loads(SAVE_PATH.read_bytes())
    else:
        roster = Roster()

    try:
        Ui(roster).run()
    finally:
        SAVE_PATH.parent.mkdir(parents=True, exist_ok=True)
        SAVE_PATH.write_bytes(pickle.dumps(roster))


if __name__ == "__main__":
    main()
