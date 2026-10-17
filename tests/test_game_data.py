import datetime
import json
import pickle
from pathlib import Path
from typing import Any

import pytest

from pqcli import random
from pqcli.config import Class, Monster, Race, StatType
from pqcli.game_data import (
    DATA_FILES,
    DataError,
    GameData,
    dump_builtin_data,
    load_game_data,
)
from pqcli.mechanic import Player, Stats, monster_task


def write(directory: Path, name: str, value: Any) -> Path:
    path = directory / f"{name}.json"
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def test_builtin_data_loads() -> None:
    data = load_game_data()
    assert data.spells[0] == "Slime Finger"
    assert data.monsters[0] == Monster("Anhkheg", 6, "chitin")
    assert data.races[0] == Race("Half Orc", [StatType.hp_max])
    assert data.classes[-1] == Class("Vermineer", [StatType.intelligence])
    assert data.combat_verbs == ("Executing {target}",)
    assert all(getattr(data, name) for name in DATA_FILES)


def test_builtin_data_keeps_quirks() -> None:
    data = load_game_data()
    names = [monster.name for monster in data.monsters]
    assert names.count("Rat") == 2
    assert Monster("Neo-Otyugh", 11, "organ ") in data.monsters
    assert any(monster.item is None for monster in data.monsters)


def test_missing_override_dir_uses_builtin(tmp_path: Path) -> None:
    assert load_game_data(tmp_path / "nope") == load_game_data()


def test_override_replaces_only_that_list(tmp_path: Path) -> None:
    write(tmp_path, "spells", ["Zap", "Bonk"])
    write(
        tmp_path,
        "races",
        [{"name": "Robot", "attr": ["STR", "hp_max", "Wisdom"]}],
    )
    builtin = load_game_data()
    data = load_game_data(tmp_path)
    assert data.spells == ("Zap", "Bonk")
    assert data.races == (
        Race("Robot", [StatType.strength, StatType.hp_max, StatType.wisdom]),
    )
    assert data.monsters == builtin.monsters
    assert data.classes == builtin.classes


def test_override_accepts_all_shapes(tmp_path: Path) -> None:
    write(tmp_path, "monsters", [{"name": "Bob", "level": 0, "item": None}])
    write(tmp_path, "weapons", [{"name": "Spoon", "quality": -1}])
    write(tmp_path, "offense_bad", [{"name": "Soggy", "quality": -2}])
    data = load_game_data(tmp_path)
    assert data.monsters == (Monster("Bob", 0, None),)
    assert data.weapons[0].name == "Spoon"
    assert data.offense_bad[0].quality == -2


def test_unknown_file_warns(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write(tmp_path, "monster", [])
    load_game_data(tmp_path)
    assert "monster.json" in capsys.readouterr().err


@pytest.mark.parametrize(
    "name,value,message",
    [
        ("spells", [], "must not be empty"),
        ("spells", {"a": 1}, "must be a list"),
        ("spells", ["ok", 3], "[1]"),
        ("monsters", [{"name": "Imp", "level": "2", "item": "x"}], "level"),
        ("monsters", [{"name": "Imp", "level": True, "item": "x"}], "level"),
        ("monsters", [{"name": "Imp", "level": 2}], "item"),
        ("monsters", [{"name": "Imp", "level": 2, "item": 1}], "item"),
        ("weapons", [{"name": "Spoon", "quality": 1, "x": 1}], "x"),
        ("races", [{"name": "Elf", "attr": ["LUCK"]}], "LUCK"),
        ("races", [{"name": "Elf", "attr": "STR"}], "attr"),
        ("combat_verbs", ["Hitting"], "{target}"),
    ],
)
def test_invalid_override_raises(
    tmp_path: Path, name: str, value: Any, message: str
) -> None:
    write(tmp_path, name, value)
    with pytest.raises(DataError) as excinfo:
        load_game_data(tmp_path)
    assert f"{name}.json" in str(excinfo.value)
    assert message in str(excinfo.value)


def test_malformed_json_raises(tmp_path: Path) -> None:
    (tmp_path / "spells.json").write_text("[oops", encoding="utf-8")
    with pytest.raises(DataError, match="spells.json"):
        load_game_data(tmp_path)


def test_non_utf8_raises(tmp_path: Path) -> None:
    (tmp_path / "spells.json").write_bytes(b'["\xff"]')
    with pytest.raises(DataError, match="spells.json"):
        load_game_data(tmp_path)


def test_override_dir_must_be_directory(tmp_path: Path) -> None:
    path = write(tmp_path, "spells", ["Zap"])
    with pytest.raises(DataError, match="not a directory"):
        load_game_data(path)


def test_combat_verbs_are_used(tmp_path: Path) -> None:
    verbs = [
        "Fighting bravely against {target}",
        "Kicking the butt of {target}",
    ]
    write(tmp_path, "combat_verbs", verbs)
    data = load_game_data(tmp_path)
    random.seed("verbs")
    seen = set()
    for _ in range(200):
        description = monster_task(data, 5, None).description
        prefix = description.split(" ")[0]
        assert prefix in {"Fighting", "Kicking"}
        assert "{target}" not in description
        seen.add(prefix)
    assert seen == {"Fighting", "Kicking"}


def test_dump_builtin_data_round_trips(tmp_path: Path) -> None:
    written = dump_builtin_data(tmp_path / "out")
    assert sorted(path.stem for path in written) == sorted(DATA_FILES)
    assert load_game_data(tmp_path / "out") == load_game_data()


def test_dump_builtin_data_refuses_to_overwrite(tmp_path: Path) -> None:
    existing = write(tmp_path, "spells", ["Mine"])
    with pytest.raises(DataError, match="spells.json"):
        dump_builtin_data(tmp_path)
    assert json.loads(existing.read_text()) == ["Mine"]
    assert list(tmp_path.iterdir()) == [existing]


def test_saved_player_survives_removed_race(tmp_path: Path) -> None:
    data = load_game_data()
    player = Player(
        name="Saved",
        birthday=datetime.datetime(2000, 1, 1),
        race=data.races[3],
        class_=data.classes[2],
        stats=Stats({stat: 10 for stat in StatType}),
    )
    blob = pickle.dumps(player)

    write(tmp_path, "races", [{"name": "Robot", "attr": ["STR"]}])
    load_game_data(tmp_path)
    restored = pickle.loads(blob)
    assert restored.race == Race("Double Hobbit", [StatType.strength])
    assert type(restored.race).__module__ == "pqcli.config"


def test_game_data_is_immutable() -> None:
    data = load_game_data()
    assert isinstance(data, GameData)
    with pytest.raises(AttributeError):
        data.spells = ()  # type: ignore[misc]
