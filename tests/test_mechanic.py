import datetime
import pickle
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
    StatsBuilder,
    create_player,
    impressive_guy,
    level_up_time,
)
from pqcli.random import Alea


def test_level_up_time_matches_upstream() -> None:
    # Math.round((20 + Math.pow(1.15, level)) * 60), pq-web 5cd39f1
    assert level_up_time(1) == 1269
    assert level_up_time(10) == 1443
    assert level_up_time(30) == 5173
    assert level_up_time(100) == 70460007


RACE = load_game_data().races[0]
CLASS = load_game_data().classes[0]


def make_simulation() -> Simulation:
    data = load_game_data()
    player = Player(
        name="Tester",
        birthday=datetime.datetime(2000, 1, 1),
        race=data.races[0],
        class_=data.classes[0],
        stats=Stats({stat: 10 for stat in StatType}),
        rng=Alea("test"),
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
        rf"the ({titles}) of the ({races})"
        rf"|({titles}) [A-Z][a-z]+ of [A-Z][a-z]+"
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


def test_prologue_fills_plot_bar() -> None:
    # upstream advances the plot bar on any task while act == 0
    random.seed("prologue")
    simulation = make_simulation()
    player = simulation.player
    positions = []
    player.connect(
        "new_task",
        lambda: positions.append(
            (player.task.description, player.quest_book.plot_bar.position)
        ),
    )
    while player.quest_book.act == 0:
        simulation.tick(100000.0)
    assert player.quest_book.plot_bar.max_ != 26  # reset by act I
    assert [position for _, position in positions[:6]] == [
        0,
        0,
        10,
        16,
        22,
        26,
    ]
    assert positions[5][0] == "Loading Act I"
    assert positions[6][0] == "Heading to the killing fields"


def test_player_rng_survives_save_and_load() -> None:
    simulation = make_simulation()
    for _ in range(50):
        simulation.tick(100000.0)
    restored = pickle.loads(pickle.dumps(simulation.player))
    assert restored.rng.state() == simulation.player.rng.state()


def test_old_save_without_rng_gets_one() -> None:
    player = make_simulation().player
    state = player.__dict__.copy()
    del state["rng"]
    restored = Player.__new__(Player)
    restored.__setstate__(state)
    assert isinstance(restored.rng, Alea)


def test_tick_draws_from_player_rng_only() -> None:
    random.seed("global")
    expected = Alea("global").uint32() % 1000
    simulation = make_simulation()
    before = simulation.player.rng.state()
    for _ in range(50):
        simulation.tick(100000.0)
    assert simulation.player.rng.state() != before
    assert random.below(1000) == expected


def test_new_game_replays_stat_roll_numbers() -> None:
    # upstream seeds the game with the state from before the stat roll
    builder = StatsBuilder(Alea("roll"))
    builder.roll()
    stats = builder.roll()
    player = create_player("New", RACE, CLASS, stats, builder.seed)
    assert player.rng.state() == builder.history[-1].seed
    with random.using(player.rng):
        rerolled = StatsBuilder(player.rng).roll()
    assert dict(rerolled) == dict(stats)


def test_unroll_restores_previous_stats_and_generator() -> None:
    builder = StatsBuilder(Alea("roll"))
    first = builder.roll()
    after_first = builder.history[-1].after
    builder.roll()
    assert builder.unroll() is first
    assert builder.seed == builder.history[-1].seed
    assert builder._rng.state() == after_first
