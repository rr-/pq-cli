"""The basic line-based UI, driven in-process through input()."""

import argparse
import signal
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from helpers import DATA, feed, hero, read_names, save_path, write_pqw
from test_pqw import played

from pqcli import pqw
from pqcli import roster as roster_module
from pqcli.config import PRIME_STATS
from pqcli.lingo import to_roman
from pqcli.mechanic import Player
from pqcli.roster import Roster
from pqcli.ui import basic
from pqcli.ui.basic import BasicUserInterface


def make_ui(
    config: Path, *players: Player, use_saves: bool = True
) -> BasicUserInterface:
    args = argparse.Namespace(use_saves=use_saves, cheats=False, colors=True)
    roster = Roster(save_path(config), list(players))
    return BasicUserInterface(roster, None, args, DATA)


@pytest.fixture
def no_play(monkeypatch: pytest.MonkeyPatch) -> list[Player]:
    """Make play() record the character instead of looping forever."""
    played: list[Player] = []
    monkeypatch.setattr(
        BasicUserInterface, "play", lambda self, player: played.append(player)
    )
    return played


# main menu ------------------------------------------------------------


def test_quit_saves_the_roster(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    ui = make_ui(tmp_path, hero("Ann"))
    feed(monkeypatch, ["7"])
    ui.run()
    out = capsys.readouterr().out
    assert "|  __/| | | (_) | (_| |" in out  # the logo
    for line in [
        "1) Create a new character",
        "2) Play as character",
        "3) Query character info",
        "4) Delete a character",
        "5) Import a character (.pqw)",
        "6) Export a character (.pqw)",
        "7) Quit",
    ]:
        assert line in out
    assert read_names(tmp_path) == ["Ann"]


def test_quit_without_saving(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ui = make_ui(tmp_path, hero("Ann"), use_saves=False)
    feed(monkeypatch, ["7"])
    ui.run()
    assert not save_path(tmp_path).exists()


def test_run_with_a_character_goes_straight_to_play(
    tmp_path: Path, no_play: list[Player]
) -> None:
    player = hero("Ann")
    ui = make_ui(tmp_path, player)
    ui.player = player
    ui.run()  # no prompts: feed() is not set up, input() would fail
    assert no_play == [player]


def test_menu_rejects_bad_input(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    ui = make_ui(tmp_path)
    feed(monkeypatch, ["", "two", "0", "8", "-1", "7"])
    ui.main_menu()
    out = capsys.readouterr().out
    assert out.count("Not a number") == 2
    assert out.count("Expected a number between 1..7") == 3


def test_confirm_accepts_several_spellings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    ui = make_ui(tmp_path)
    answers = ["Y", "yes", "1", "N", "No", "0"]
    feed(monkeypatch, ["?", *answers])
    assert [ui.confirm("Sure?") for _ in answers] == [True] * 3 + [False] * 3
    assert capsys.readouterr().out.count("Sure? [y/n] ") == 7


@pytest.mark.parametrize("choice", ["2", "3", "4", "6"])
def test_choosing_with_no_characters(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    choice: str,
) -> None:
    ui = make_ui(tmp_path)
    feed(monkeypatch, [choice, "7"])
    ui.main_menu()
    assert "No characters to choose from!" in capsys.readouterr().out


# creating -------------------------------------------------------------


def test_create_rerolls_until_accepted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    no_play: list[Player],
) -> None:
    ui = make_ui(tmp_path)
    # create, name, race, class, reroll twice, accept, don't play, quit
    feed(monkeypatch, ["1", "Rolf", "2", "3", "n", "n", "y", "n", "7"])
    ui.main_menu()

    out = capsys.readouterr().out
    assert out.count("Total: ") == 3
    for race in DATA.races:
        assert f") {race.name}\n" in out
    assert "Do you want to play as your new character? [y/n] n" in out
    assert no_play == []

    [player] = ui.roster.players
    assert player.name == "Rolf"
    assert player.race == DATA.races[1]
    assert player.class_ == DATA.classes[2]

    # the accepted stats are the last ones shown
    last_shown = out.split("Is this okay?")[-2].splitlines()[-7:-1]
    assert last_shown == [
        f"{stat.value}: {player.stats[stat]}" for stat in PRIME_STATS
    ]
    assert read_names(tmp_path) == ["Rolf"]  # saved on quit


def test_create_then_play(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    no_play: list[Player],
) -> None:
    ui = make_ui(tmp_path)
    feed(monkeypatch, ["Rolf", "1", "1", "y", "y"])
    player = ui.create_player()
    assert no_play == [player]
    assert ui.roster.players == [player]


def test_create_cancelled_by_empty_name(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    ui = make_ui(tmp_path)
    feed(monkeypatch, [""])
    assert ui.create_player() is None
    assert "Cancelled." in capsys.readouterr().out
    assert ui.roster.players == []


# playing --------------------------------------------------------------


def test_play_from_the_menu(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    no_play: list[Player],
) -> None:
    ann, bob = hero("Ann"), hero("Bob")
    ui = make_ui(tmp_path, ann, bob)
    feed(monkeypatch, ["2", "x", "3", "2", "7"])
    ui.main_menu()
    assert no_play == [bob]
    out = capsys.readouterr().out
    assert "Choose your character:\n1) Ann\n2) Bob\n" in out
    assert "Expected a number between 1..2" in out


class StopPlaying(Exception):
    pass


class FastClock:
    """Stands in for datetime: every now() is a minute after the last."""

    current = datetime(2024, 1, 1)

    @classmethod
    def now(cls) -> datetime:
        cls.current += timedelta(minutes=1)
        return cls.current


@pytest.fixture
def game_loop(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    """Run play() on a fast clock, stopping it after 800 rounds.

    Returns the requested sleeps.
    """
    sleeps: list[float] = []

    def sleep(seconds: float) -> None:
        sleeps.append(seconds)
        if len(sleeps) == 800:
            raise StopPlaying

    monkeypatch.setattr(FastClock, "current", datetime(2024, 1, 1))
    monkeypatch.setattr(basic, "datetime", FastClock)
    monkeypatch.setattr(roster_module, "datetime", FastClock)
    monkeypatch.setattr(basic.time, "sleep", sleep)
    return sleeps


def test_play_prints_the_sheet_on_level_up(
    tmp_path: Path,
    game_loop: list[float],
    capsys: pytest.CaptureFixture[str],
) -> None:
    # played(0) reaches level 2 within 800 minute-long ticks
    player = played(0).player
    ui = make_ui(tmp_path, player, use_saves=False)
    with pytest.raises(StopPlaying):
        ui.play(player)

    out = capsys.readouterr().out
    assert out.startswith("Playing as Exportée\n")
    sheets = out.split("--- Character Sheet ---")[1:]
    assert len(sheets) == 2
    assert "Level: 1\n" in sheets[0]
    assert "Level: 2\n" in sheets[1]
    assert player.level == 2
    # ticks are a minute late, so play() never waits
    assert set(game_loop) == {0}
    assert not save_path(tmp_path).exists()


def test_play_saves_every_five_minutes(
    tmp_path: Path, game_loop: list[float], monkeypatch: pytest.MonkeyPatch
) -> None:
    player = played(0).player
    ui = make_ui(tmp_path, player)
    saves: list[datetime] = []
    real_save = ui.roster.save

    def save() -> None:
        saves.append(FastClock.current)
        real_save()

    monkeypatch.setattr(ui.roster, "save", save)
    with pytest.raises(StopPlaying):
        ui.play(player)

    assert len(saves) > 100
    gaps = {b - a for a, b in zip(saves, saves[1:], strict=False)}
    assert min(gaps) >= timedelta(minutes=5)
    assert read_names(tmp_path) == ["Exportée"]


def test_play_waits_out_the_rest_of_a_tick(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With no time passing, each round sleeps a full 100 ms."""
    sleeps: list[float] = []

    class FrozenClock:
        @staticmethod
        def now() -> datetime:
            return datetime(2024, 1, 1)

    def sleep(seconds: float) -> None:
        sleeps.append(seconds)
        if len(sleeps) == 3:
            raise StopPlaying

    monkeypatch.setattr(basic, "datetime", FrozenClock)
    monkeypatch.setattr(basic.time, "sleep", sleep)
    player = played(0).player
    with pytest.raises(StopPlaying):
        make_ui(tmp_path, use_saves=False).play(player)
    assert sleeps == [0.1, 0.1, 0.1]


# info -----------------------------------------------------------------


def test_info_for_a_seasoned_character(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    player = hero("Ann", ticks=20000)
    assert player.spell_book.best is not None
    ui = make_ui(tmp_path, player)
    feed(monkeypatch, ["3", "1", "7"])
    ui.main_menu()

    out = capsys.readouterr().out
    assert "Name: Ann\n" in out
    assert f"Race: {player.race.name}\n" in out
    assert f"Class: {player.class_.name}\n" in out
    assert f"Level: {player.level}\n" in out
    assert "No spells memorized yet." not in out
    for spell in player.spell_book:
        assert f"\n{spell.name} " in out
    assert f"Gold: {player.inventory.gold}\n" in out
    for item in player.inventory:
        assert f"{item.name}: {item.quantity}\n" in out
    assert f"Current quest: {player.quest_book.current_quest}\n" in out
    assert player.task is not None
    assert f"Current task: {player.task.description}\n" in out


def test_info_for_a_new_character(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    player = played(0, seed="new").player
    player.task = None
    make_ui(tmp_path).print_player_info(player)
    out = capsys.readouterr().out
    assert "No spells memorized yet." in out
    assert f"Current act: {to_roman(player.quest_book.act)}\n" in out
    assert "Current task: ?\n" in out


# deleting -------------------------------------------------------------


def test_delete_after_confirming(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    ann, bob = hero("Ann"), hero("Bob")
    ui = make_ui(tmp_path, ann, bob)
    feed(monkeypatch, ["4", "1", "n", "4", "1", "y", "7"])
    ui.main_menu()
    assert ui.roster.players == [bob]
    assert capsys.readouterr().out.count("Ann") >= 2
    assert read_names(tmp_path) == ["Bob"]


# importing and exporting ----------------------------------------------


def test_import(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    write_pqw(tmp_path / "cid.pqw", hero("Cid"), online=True)
    ui = make_ui(tmp_path / "config", hero("Ann"))
    feed(monkeypatch, ["5", "  ~/cid.pqw  ", "7"])
    ui.main_menu()

    out = capsys.readouterr().out
    assert "Warning: dropped 'online': pqcli plays offline only\n" in out
    assert "Imported Cid.\n" in out
    assert [p.name for p in ui.roster.players] == ["Ann", "Cid"]
    assert read_names(tmp_path / "config") == ["Ann", "Cid"]


def test_import_without_saving(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = write_pqw(tmp_path / "cid.pqw", hero("Cid"))
    ui = make_ui(tmp_path, use_saves=False)
    feed(monkeypatch, [str(source)])
    ui.import_player()
    assert [p.name for p in ui.roster.players] == ["Cid"]
    assert not save_path(tmp_path).exists()


@pytest.mark.parametrize(
    ("answer", "message"),
    [("", "Cancelled."), ("missing.pqw", "Cannot import: cannot read")],
)
def test_import_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    answer: str,
    message: str,
) -> None:
    monkeypatch.chdir(tmp_path)
    ui = make_ui(tmp_path)
    feed(monkeypatch, [answer])
    ui.import_player()
    assert message in capsys.readouterr().out
    assert ui.roster.players == []
    assert not save_path(tmp_path).exists()


def test_export_to_the_default_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    ui = make_ui(tmp_path, hero("Ann"), hero("Bob"))
    feed(monkeypatch, ["6", "2", "", "7"])
    ui.main_menu()
    out = capsys.readouterr().out
    assert "Export to .pqw file [Bob.pqw]: " in out
    assert "Exported Bob to Bob.pqw.\n" in out
    assert pqw.read_file(tmp_path / "Bob.pqw", DATA)[0].name == "Bob"


def test_export_to_a_chosen_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    ui = make_ui(tmp_path, hero("Ann"))
    feed(monkeypatch, [" ~/out.pqw "])
    ui.export_player(ui.roster.players[0])
    assert "Exported Ann to ~/out.pqw.\n" in capsys.readouterr().out
    assert pqw.read_file(tmp_path / "out.pqw", DATA)[0].name == "Ann"


def test_export_never_overwrites(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    target = tmp_path / "out.pqw"
    target.write_text("mine")
    ui = make_ui(tmp_path, hero("Ann"))
    feed(monkeypatch, [str(target)])
    ui.export_player(ui.roster.players[0])
    assert f"Cannot export: {target} already exists" in capsys.readouterr().out
    assert target.read_text() == "mine"


# Ctrl+C ---------------------------------------------------------------


@pytest.mark.parametrize("use_saves", [True, False])
def test_ctrl_c_saves_and_exits(tmp_path: Path, use_saves: bool) -> None:
    ui = make_ui(tmp_path, hero("Ann"), use_saves=use_saves)
    handler = signal.getsignal(signal.SIGINT)
    assert callable(handler)
    with pytest.raises(SystemExit) as ex:
        handler(signal.SIGINT, None)
    assert ex.value.code == 0
    assert save_path(tmp_path).exists() == use_saves
    assert ui.roster.players  # still there
