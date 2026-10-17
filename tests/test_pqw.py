import base64
import datetime
import json

import pytest
from upstream import bridge

from pqcli.config import StatType
from pqcli.game_data import load_game_data
from pqcli.mechanic import Player, Simulation, Stats
from pqcli.pqw import PqwError, decode, encode, export_game, import_game
from pqcli.random import Alea

DATA = load_game_data()


def played(ticks: int, seed: str = "pqw") -> Simulation:
    player = Player(
        name="Exportée",
        birthday=datetime.datetime(2020, 2, 2, 12, 0, 0),
        race=DATA.races[5],
        class_=DATA.classes[7],
        stats=Stats({stat: 9 for stat in StatType}),
        rng=Alea(seed),
    )
    simulation = Simulation(player, DATA)
    simulation.tick(0)
    for _ in range(ticks):
        simulation.tick(100)
    return simulation


def test_encode_decode_round_trip() -> None:
    game = {"Traits": {"Name": "Zoë 🐉"}, "act": 3}
    assert decode(encode(game)) == game


def test_decode_ignores_whitespace() -> None:
    text = encode({"Traits": {"Name": "x"}})
    assert decode("\n".join(text[i : i + 10] for i in range(0, 99, 10)))


def test_decode_reads_old_latin1_saves() -> None:
    # before 2022 the web version stored base64 of the raw JS string
    raw = json.dumps({"Traits": {"Name": "Jürgen"}}, ensure_ascii=False)
    text = base64.b64encode(raw.encode("latin-1")).decode()
    assert decode(text)["Traits"]["Name"] == "Jürgen"


@pytest.mark.parametrize(
    "text",
    [
        "not base64 at all!",
        base64.b64encode(b"not json").decode(),
        base64.b64encode(b"[1, 2]").decode(),
        base64.b64encode(b'{"act": 1}').decode(),
    ],
)
def test_decode_rejects_garbage(text: str) -> None:
    with pytest.raises(PqwError, match="not a .pqw file"):
        decode(text)


def test_import_reports_missing_fields() -> None:
    game = export_game(played(500).player, DATA)
    del game["ExpBar"]
    with pytest.raises(PqwError, match="ExpBar"):
        import_game(game, DATA)


def test_import_rejects_bad_numbers() -> None:
    game = export_game(played(500).player, DATA)
    game["Traits"]["Level"] = "lots"
    with pytest.raises(PqwError, match="Traits.Level"):
        import_game(game, DATA)


def test_import_warns_about_online_play() -> None:
    game = export_game(played(500).player, DATA)
    game["online"] = {"realm": "Alpaquil", "passkey": 1}
    game["motto"] = "hi"
    _player, warnings = import_game(game, DATA)
    assert len(warnings) == 2
    assert "online" in warnings[0]


def test_import_merges_renamed_spells() -> None:
    game = export_game(played(500).player, DATA)
    game["Spells"] = [
        ["Inoculate", "II"],
        ["Slime Finger", "I"],
        ["Innoculate", "III"],
    ]
    player, _warnings = import_game(game, DATA)
    assert [(s.name, s.level) for s in player.spell_book] == [
        ("Slime Finger", 1),
        ("Inoculate", 5),
    ]


def test_import_keeps_unknown_race_and_class() -> None:
    game = export_game(played(500).player, DATA)
    game["Traits"]["Race"] = "Moon Wombat"
    player, _warnings = import_game(game, DATA)
    assert player.race.name == "Moon Wombat"
    assert player.race.attr == []


def test_export_of_unplayed_character() -> None:
    player = Player(
        name="Fresh",
        birthday=datetime.datetime(2020, 2, 2),
        race=DATA.races[0],
        class_=DATA.classes[0],
        stats=Stats({stat: 9 for stat in StatType}),
    )
    game = export_game(player, DATA)
    assert game["kill"] == "Loading...."
    assert len(game["queue"]) == 5
    assert player.task is None  # exported a copy


@pytest.mark.parametrize("ticks", [0, 1, 25, 3000, 40000, 123457])
def test_round_trip_keeps_playing_identically(ticks: int) -> None:
    original = played(ticks)
    copy, _warnings = import_game(
        decode(encode(export_game(original.player, DATA))), DATA
    )
    assert bridge.snapshot(copy) == bridge.snapshot(original.player)
    resumed = Simulation(copy, DATA)
    assert bridge.run(resumed, 10**8, 2000) == bridge.run(
        original, 10**8, 2000
    )
