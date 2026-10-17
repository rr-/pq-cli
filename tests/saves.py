"""Characters, rosters and .pqw files for the UI and CLI tests."""

from pathlib import Path

from test_pqw import played

from pqcli import pqw
from pqcli.game_data import load_game_data
from pqcli.mechanic import Player
from pqcli.roster import Roster

DATA = load_game_data()


def hero(name: str = "Exportée", ticks: int = 300) -> Player:
    """A character that has played for a while."""
    player = played(ticks).player
    player.name = name
    return player


def save_path(config: Path) -> Path:
    """Where pqcli keeps its roster with XDG_CONFIG_HOME set to config."""
    return config / "pqcli" / "save.dat"


def write_roster(config: Path, *players: Player) -> Path:
    path = save_path(config)
    Roster(path, list(players)).save()
    return path


def read_names(config: Path) -> list[str]:
    return [player.name for player in Roster.load(save_path(config)).players]


def write_pqw(path: Path, player: Player, *, online: bool = False) -> Path:
    """Write player as a .pqw; online adds fields the import warns about."""
    game = pqw.export_game(player, DATA)
    if online:
        game["online"] = {"realm": "Alpaquil", "passkey": 1}
    path.write_text(pqw.encode(game), encoding="ascii")
    return path
