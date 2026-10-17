import datetime
import re

import pytest

from pqcli import random
from pqcli.config import PRIME_STATS, StatType
from pqcli.game_data import load_game_data
from pqcli.lingo import plural
from pqcli.mechanic import (
    Player,
    Simulation,
    Stats,
    impressive_guy,
    level_up_time,
)


def test_level_up_time_matches_upstream() -> None:
    # Math.round((20 + Math.pow(1.15, level)) * 60), pq-web 5cd39f1
    assert level_up_time(1) == 1269
    assert level_up_time(10) == 1443
    assert level_up_time(30) == 5173
    assert level_up_time(100) == 70460007


def make_simulation() -> Simulation:
    data = load_game_data()
    player = Player(
        name="Tester",
        birthday=datetime.datetime(2000, 1, 1),
        race=data.races[0],
        class_=data.classes[0],
        stats=Stats({stat: 10 for stat in StatType}),
    )
    return Simulation(player, data)


def test_quest_length_matches_upstream() -> None:
    # QuestBar.reset(50 + Random(100)), pq-web f7d5e83
    random.seed("quests")
    simulation = make_simulation()
    lengths = set()
    for _ in range(2000):
        simulation.complete_quest()
        lengths.add(simulation.player.quest_book.quest_bar.max_)
    assert min(lengths) == 50
    assert max(lengths) == 149


def test_weighted_stat_gain_skips_hp_and_mp(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # the "favor the best stat" branch only covers prime stats, pq-web 48c42e6
    monkeypatch.setattr(random, "odds", lambda chance, out_of: False)
    random.seed("stats")
    player = make_simulation().player
    player.stats.increment(StatType.hp_max, 1000)
    for _ in range(500):
        player.win_stat()
    assert player.stats[StatType.hp_max] == 1010
    assert player.stats[StatType.mp_max] == 10
    assert sum(player.stats[stat] for stat in PRIME_STATS) == 60 + 500


def fake_below(monkeypatch: pytest.MonkeyPatch, *values: int) -> None:
    queue = list(values)
    monkeypatch.setattr(random, "below", lambda num: queue.pop(0) % num)


def full_inventory(rows: int) -> Simulation:
    simulation = make_simulation()
    for i in range(rows):
        simulation.player.inventory.add(f"item {i}", 1)
    return simulation


def test_win_item_adds_new_item_below_cap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    simulation = full_inventory(10)
    random.seed("items")
    simulation.player.win_item(simulation.data)
    assert len(simulation.player.inventory) == 11


def test_win_item_repeats_existing_item_past_cap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Max(250, Random(999)) < rows: add one of a random row, pq-web 3cbd386
    simulation = full_inventory(300)
    inventory = simulation.player.inventory
    fake_below(monkeypatch, 260, 6)  # rows include Gold, so 6 is "item 5"
    simulation.player.win_item(simulation.data)
    assert len(inventory) == 300
    assert inventory[5].quantity == 2


def test_win_item_can_pick_gold_row(monkeypatch: pytest.MonkeyPatch) -> None:
    simulation = full_inventory(300)
    fake_below(monkeypatch, 0, 0)
    simulation.player.win_item(simulation.data)
    assert simulation.player.inventory.gold == 1
    assert len(simulation.player.inventory) == 300


def test_win_item_past_cap_can_still_add_new_item(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    simulation = full_inventory(300)
    random.seed("items")
    fake_below(monkeypatch, 301, 0, 0, 0)
    simulation.player.win_item(simulation.data)
    assert len(simulation.player.inventory) == 301


def test_impressive_guy_formats() -> None:
    # pq-web cea0d8c
    data = load_game_data()
    titles = "|".join(re.escape(title) for title in data.impressive_titles)
    races = "|".join(re.escape(plural(race.name)) for race in data.races)
    pattern = re.compile(
        rf"the ({titles}) of the ({races})|({titles}) [A-Z][a-z]+ of [A-Z][a-z]+"
    )
    random.seed("guys")
    guys = [impressive_guy(data) for _ in range(200)]
    for guy in guys:
        assert pattern.fullmatch(guy), guy
    assert any(guy.startswith("the ") for guy in guys)
    assert not all(guy.startswith("the ") for guy in guys)


def test_impressive_titles_match_upstream() -> None:
    assert load_game_data().impressive_titles[-3:] == (
        "Chancellor",
        "Baroness",
        "Inquistor",  # sic, as upstream
    )


def test_cinematic_text_matches_upstream() -> None:
    random.seed("cinematics")
    simulation = make_simulation()
    for _ in range(60):
        simulation.interplot_cinematic()
    texts = [task.description for task in simulation.player.queue]
    assert any("You've reached the kind protection of " in t for t in texts)
    assert any(t.endswith("news!? -- Oh yes, of course") for t in texts)


def test_quest_log_keeps_100_quests() -> None:
    quest_book = make_simulation().player.quest_book
    for i in range(150):
        quest_book.add_quest(f"quest {i}")
    assert len(quest_book.quests) == 100
    assert quest_book.quests[-1] == "quest 149"
