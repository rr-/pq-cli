"""pqcli's command line, run in-process so coverage sees it."""

import json
from collections.abc import Callable
from pathlib import Path

import pytest
from helpers import (
    DATA,
    feed,
    hero,
    read_names,
    save_path,
    write_pqw,
    write_roster,
)

import pqcli.__main__ as cli
from pqcli import pqw
from pqcli.game_data import DATA_FILES
from pqcli.mechanic import Player
from pqcli.roster import Roster
from pqcli.ui.basic import BasicUserInterface
from pqcli.ui.curses import CursesUserInterface

Run = Callable[..., int]


@pytest.fixture
def config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point the save and data paths at tmp_path/config."""
    config = tmp_path / "config"
    monkeypatch.setattr(cli, "SAVE_PATH", save_path(config))
    monkeypatch.setattr(cli, "DATA_PATH", config / "pqcli" / "data")
    return config


class NoCurses:
    """Fails the test instead of taking over the terminal with curses."""

    def __init__(self, *args: object) -> None:
        raise AssertionError("the curses UI was started")


@pytest.fixture(autouse=True)
def _no_curses(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "CursesUserInterface", NoCurses)


@pytest.fixture
def run(config: Path, monkeypatch: pytest.MonkeyPatch) -> Run:
    """Call main() with the given arguments and return its exit code."""

    def run(*args: str) -> int:
        monkeypatch.setattr("sys.argv", ["pqcli", *args])
        try:
            cli.main()
        except SystemExit as ex:
            assert isinstance(ex.code, int | None)
            return ex.code or 0
        return 0

    return run


def test_defaults_to_the_curses_ui(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.undo()
    monkeypatch.setattr("sys.argv", ["pqcli"])
    args = cli.parse_args()
    assert args.ui is CursesUserInterface
    assert args.use_saves
    assert args.colors
    assert not args.cheats


def test_list_saves(
    run: Run, config: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write_roster(config, hero("Ann"), hero("Bob"))
    assert run("--list-saves") == 0
    assert capsys.readouterr().out == "1. Ann\n2. Bob\n"


def test_list_saves_when_there_are_none(
    run: Run, config: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert run("--list-saves") == 0
    assert capsys.readouterr().out == ""
    # no first-run character creation, and nothing written
    assert not config.exists()


@pytest.mark.parametrize(
    "num",
    [
        "3",
        "0",
        "-1",
    ],
)
def test_load_save_rejects_unknown_character(
    run: Run,
    config: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    num: str,
) -> None:
    write_roster(config, hero("Ann"), hero("Bob"))
    feed(monkeypatch, ["7"])
    monkeypatch.setattr(BasicUserInterface, "play", lambda self, p: None)
    assert run("--basic", "--load-save", num) == 1
    err = capsys.readouterr().err
    assert err == "Invalid player. Available players:\n1. Ann\n2. Bob\n"


def test_load_save_plays_the_character_and_saves(
    run: Run, config: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    write_roster(config, hero("Ann"), hero("Bob"))
    played: list[Player] = []

    def play(self: BasicUserInterface, player: Player) -> None:
        played.append(player)
        player.name = "Bobby"

    monkeypatch.setattr(BasicUserInterface, "play", play)
    assert run("--basic", "--load-save", "2") == 0
    assert [p.name for p in played] == ["Bobby"]
    assert read_names(config) == ["Ann", "Bobby"]


def test_no_save_leaves_the_roster_alone(
    run: Run, config: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    write_roster(config, hero("Ann"))

    def play(self: BasicUserInterface, player: Player) -> None:
        player.name = "Changed"

    monkeypatch.setattr(BasicUserInterface, "play", play)
    assert run("--basic", "--no-save", "--load-save", "1") == 0
    assert read_names(config) == ["Ann"]


def test_saves_even_when_the_ui_crashes(
    run: Run, config: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    write_roster(config, hero("Ann"))

    def play(self: BasicUserInterface, player: Player) -> None:
        player.name = "Crashed"
        raise RuntimeError("boom")

    monkeypatch.setattr(BasicUserInterface, "play", play)
    with pytest.raises(RuntimeError, match="boom"):
        run("--basic", "--load-save", "1")
    assert read_names(config) == ["Crashed"]


def test_dump_data(
    run: Run, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    target = tmp_path / "words"
    assert run("--dump-data", str(target)) == 0
    assert capsys.readouterr().out == (
        f"Wrote {len(DATA_FILES)} files to {target}\n"
    )
    assert sorted(p.stem for p in target.iterdir()) == sorted(DATA_FILES)


def test_dump_data_refuses_to_overwrite(
    run: Run, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    target = tmp_path / "words"
    target.mkdir()
    existing = target / f"{next(iter(DATA_FILES))}.json"
    existing.write_text("mine")
    assert run("--dump-data", str(target)) == 1
    assert capsys.readouterr().err.startswith("pqcli: refusing to overwrite")
    assert existing.read_text() == "mine"


def test_data_dir_must_be_a_directory(
    run: Run, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    not_dir = tmp_path / "file"
    not_dir.write_text("")
    assert run("--data-dir", str(not_dir), "--list-saves") == 1
    assert capsys.readouterr().err == f"pqcli: {not_dir}: not a directory\n"


def test_data_dir_with_broken_list(
    run: Run, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "races.json").write_text("{not json")
    assert run("--data-dir", str(tmp_path), "--list-saves") == 1
    err = capsys.readouterr().err
    assert err.startswith("pqcli: ")
    assert "races.json" in err


def test_default_data_dir_is_used(
    run: Run, config: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data_dir = config / "pqcli" / "data"
    data_dir.mkdir(parents=True)
    (data_dir / "races.json").write_text("[]")
    assert run("--list-saves") == 1
    assert "races.json" in capsys.readouterr().err


def test_import_saves(
    run: Run,
    config: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    write_roster(config, hero("Ann"))
    first = write_pqw(tmp_path / "a.pqw", hero("Bob"))
    second = write_pqw(tmp_path / "b.pqw", hero("Cid"), online=True)

    assert run("--import-save", str(first), "--import-save", str(second)) == 0
    out, err = capsys.readouterr()
    assert out == "Imported Bob\nImported Cid\n"
    assert (
        err == f"pqcli: {second}: dropped 'online': pqcli plays offline only\n"
    )
    assert read_names(config) == ["Ann", "Bob", "Cid"]


def test_import_saves_without_saving(
    run: Run, config: Path, tmp_path: Path
) -> None:
    source = write_pqw(tmp_path / "a.pqw", hero("Bob"))
    assert run("--no-save", "--import-save", str(source)) == 0
    assert not save_path(config).exists()


def test_import_stops_at_the_first_bad_file(
    run: Run,
    config: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    good = write_pqw(tmp_path / "a.pqw", hero("Bob"))
    missing = tmp_path / "missing.pqw"
    assert run("--import-save", str(good), "--import-save", str(missing)) == 1
    assert capsys.readouterr().err.startswith(f"pqcli: cannot read {missing}")
    assert not save_path(config).exists()


def test_export_save(
    run: Run,
    config: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    write_roster(config, hero("Ann"), hero("Bob"))
    target = tmp_path / "bob.pqw"
    assert run("--export-save", "2", str(target)) == 0
    assert capsys.readouterr().out == f"Exported Bob to {target}\n"
    assert pqw.read_file(target, DATA)[0].name == "Bob"


@pytest.mark.parametrize("num", ["0", "3", "x", "-1"])
def test_export_save_rejects_unknown_character(
    run: Run,
    config: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    num: str,
) -> None:
    write_roster(config, hero("Ann"), hero("Bob"))
    target = tmp_path / "x.pqw"
    assert run("--export-save", num, str(target)) == 1
    assert capsys.readouterr().err == (
        "Invalid player. Available players:\n1. Ann\n2. Bob\n"
    )
    assert not target.exists()


def test_export_save_never_overwrites(
    run: Run,
    config: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    write_roster(config, hero("Ann"))
    target = tmp_path / "x.pqw"
    target.write_text("mine")
    assert run("--export-save", "1", str(target)) == 1
    assert capsys.readouterr().err == f"pqcli: {target} already exists\n"
    assert target.read_text() == "mine"


# first run ------------------------------------------------------------


def test_first_run_creates_a_character_then_shows_the_menu(
    run: Run,
    config: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    race, class_ = DATA.races[2], DATA.classes[3]
    # name, race, class, accept the stats, then quit from the main menu
    feed(monkeypatch, ["Newbie", "3", "4", "y", "7"])
    assert run("--basic") == 0

    out = capsys.readouterr().out
    assert out.startswith(
        "No saved characters found. Starting first-run character creation."
    )
    # no "play now?" question on the first run
    assert "Do you want to play" not in out
    assert "1) Create a new character" in out

    [player] = Roster.load(save_path(config)).players
    assert player.name == "Newbie"
    assert player.race == race
    assert player.class_ == class_


def test_first_run_can_be_retried(
    run: Run,
    config: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    feed(monkeypatch, ["", "maybe", "y", "Second", "1", "1", "y", "7"])
    assert run("--basic") == 0
    assert read_names(config) == ["Second"]


def test_first_run_gives_up_without_a_character(
    run: Run,
    config: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    feed(monkeypatch, ["", "n"])
    assert run("--basic") == 1
    out, err = capsys.readouterr()
    assert "Cancelled." in out
    assert err == "A character is required for first run.\n"
    assert not save_path(config).exists()


def test_first_run_is_skipped_with_characters(
    run: Run, config: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    write_roster(config, hero("Ann"))
    feed(monkeypatch, ["7"])
    assert run("--basic") == 0
    assert read_names(config) == ["Ann"]


def test_dump_data_writes_valid_json(run: Run, tmp_path: Path) -> None:
    target = tmp_path / "words"
    run("--dump-data", str(target))
    for path in target.iterdir():
        json.loads(path.read_text(encoding="utf-8"))
