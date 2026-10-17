import datetime

import pytest

from pqcli import random
from pqcli.config import PRIME_STATS, StatType
from pqcli.game_data import load_game_data
from pqcli.mechanic import Player, Simulation, Stats, level_up_time


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
