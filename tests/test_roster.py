import pickle
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from helpers import hero

from pqcli import roster as roster_module
from pqcli.roster import Roster

START = datetime(2024, 1, 1, 12, 0, 0)


class Clock:
    """Stands in for datetime in pqcli.roster; only now() is used."""

    current = START

    @classmethod
    def now(cls) -> datetime:
        return cls.current

    @classmethod
    def advance(cls, seconds: float) -> None:
        cls.current += timedelta(seconds=seconds)


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> type[Clock]:
    monkeypatch.setattr(Clock, "current", START)
    monkeypatch.setattr(roster_module, "datetime", Clock)
    return Clock


def names(path: Path) -> list[str]:
    return [player.name for player in pickle.loads(path.read_bytes())]


def test_load_missing_file_gives_empty_roster(tmp_path: Path) -> None:
    path = tmp_path / "nowhere" / "save.dat"
    roster = Roster.load(path)
    assert roster.players == []
    assert roster.path == path
    assert not path.parent.exists()


def test_load_accepts_a_string_path(tmp_path: Path) -> None:
    path = tmp_path / "save.dat"
    Roster(path, [hero("Ann")]).save()
    assert Roster.load(str(path)).path == path


def test_save_then_load_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "deep" / "dir" / "save.dat"
    player = hero("Ann", ticks=1000)
    Roster(path, [player, hero("Bob")]).save()

    loaded = Roster.load(path).players
    assert [p.name for p in loaded] == ["Ann", "Bob"]
    assert loaded[0].level == player.level
    assert loaded[0].inventory.gold == player.inventory.gold
    assert loaded[0].quest_book.quests == player.quest_book.quests


def test_save_keeps_the_previous_save_as_old(tmp_path: Path) -> None:
    path = tmp_path / "save.dat"
    old = tmp_path / "save.dat.old"
    roster = Roster(path, [hero("Ann")])

    roster.save()
    assert names(path) == ["Ann"]
    assert not old.exists()

    roster.players.append(hero("Bob"))
    roster.save()
    assert names(path) == ["Ann", "Bob"]
    assert names(old) == ["Ann"]

    roster.players.pop(0)
    roster.save()
    assert names(path) == ["Bob"]
    assert names(old) == ["Ann", "Bob"]

    assert sorted(p.name for p in tmp_path.iterdir()) == [
        "save.dat",
        "save.dat.old",
    ]


def test_save_periodically_waits_five_minutes(
    tmp_path: Path, clock: type[Clock]
) -> None:
    path = tmp_path / "save.dat"
    roster = Roster(path, [hero("Ann")])

    clock.advance(299)
    roster.save_periodically()
    assert not path.exists()

    clock.advance(1)
    roster.save_periodically()
    assert names(path) == ["Ann"]

    # the timer starts over after a save
    roster.players.append(hero("Bob"))
    clock.advance(299)
    roster.save_periodically()
    assert names(path) == ["Ann"]

    clock.advance(1)
    roster.save_periodically()
    assert names(path) == ["Ann", "Bob"]


def test_manual_save_restarts_the_periodic_timer(
    tmp_path: Path, clock: type[Clock]
) -> None:
    path = tmp_path / "save.dat"
    roster = Roster(path, [hero("Ann")])

    clock.advance(200)
    roster.save()
    roster.players.append(hero("Bob"))

    clock.advance(200)
    roster.save_periodically()
    assert names(path) == ["Ann"]

    clock.advance(100)
    roster.save_periodically()
    assert names(path) == ["Ann", "Bob"]
