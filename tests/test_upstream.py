"""Compare pqcli with Progress Quest web, run headless in node.

`just test` fetches upstream first; see tests/upstream/fetch.py. Without
node or the fetched files, these tests are skipped.
"""

from typing import Any, cast

import pytest
from upstream import bridge

from pqcli import random
from pqcli.game_data import DATA_FILES, load_game_data
from pqcli.lingo import generate_name
from pqcli.mechanic import (
    Simulation,
    impressive_guy,
    monster_task,
    named_monster,
    special_item,
)
from pqcli.pqw import decode, encode, export_game, import_game
from pqcli.random import Alea, RngState

pytestmark = pytest.mark.skipif(
    bridge.unavailable_reason() is not None,
    reason=bridge.unavailable_reason() or "",
)

DATA = load_game_data()
STATES = [list(Alea(f"state {i}").state()) for i in range(200)]


def test_word_lists_match_upstream() -> None:
    (lists,) = bridge.run_harness([{"cmd": "lists"}])
    for name in DATA_FILES:
        if name == "combat_verbs":
            continue  # pqcli only; upstream always says "Executing"
        assert bridge.encode_list(name, DATA) == lists[bridge.LISTS[name]]


def compare_calls(
    fn: str,
    args: list[Any],
    ours: Any,
    convert: Any = lambda result: result,
    **extra: Any,
) -> None:
    requests = [
        {"cmd": "call", "fn": fn, "args": args, "rng": state, **extra}
        for state in STATES
    ]
    for state, theirs in zip(STATES, bridge.run_harness(requests)):
        rng = Alea.from_state(cast(RngState, tuple(state)))
        with random.using(rng):
            result = ours()
        assert (result, list(rng.state())) == (
            convert(theirs["result"]),
            theirs["rng"],
        ), f"{fn}({args}) from state {state}"


def kill_task(level: int, monster: Any) -> tuple[str, int]:
    task = monster_task(DATA, level, monster)
    return task.description, task.duration


def upstream_kill_task(level: int) -> Any:
    # Dequeue() turns MonsterTask's result into the task like this
    return lambda result: (
        "Executing " + result["description"],
        (2 * 3 * result["level"] * 1000) // level,
    )


@pytest.mark.parametrize("level", [1, 2, 5, 10, 20, 40, 80, 150])
def test_monster_task_matches_upstream(level: int) -> None:
    compare_calls(
        "MonsterTask",
        [level],
        lambda: kill_task(level, None),
        upstream_kill_task(level),
        questmonster="",
    )


@pytest.mark.parametrize("level", [1, 10, 40])
def test_monster_task_with_quest_monster_matches_upstream(
    level: int,
) -> None:
    index = 25
    monster = DATA.monsters[index]
    compare_calls(
        "MonsterTask",
        [level],
        lambda: kill_task(level, monster),
        upstream_kill_task(level),
        questmonster=bridge.encode_monster(monster),
        questmonsterindex=index,
    )


def test_named_monster_matches_upstream() -> None:
    compare_calls("NamedMonster", [12], lambda: named_monster(DATA, 12))


def test_impressive_guy_matches_upstream() -> None:
    compare_calls("ImpressiveGuy", [], lambda: impressive_guy(DATA))


def test_special_item_matches_upstream() -> None:
    compare_calls("SpecialItem", [], lambda: special_item(DATA))


def test_generate_name_matches_upstream() -> None:
    compare_calls("GenerateName", [], generate_name)


@pytest.mark.parametrize(
    "seed,race,class_",
    [
        ("alpha", "Half Orc", "Ur-Paladin"),
        ("beta", "Land Squid", "Vermineer"),
        ("gamma", "Talking Pony", "Mage Illusioner"),
    ],
)
def test_game_matches_upstream(seed: str, race: str, class_: str) -> None:
    # Play both from the same character and generator state, 100 ms per
    # tick, and compare the whole state, generator included, each time a
    # task completes.
    tasks = 3000
    ticks = 100 * tasks * 1000
    spec = bridge.make_spec(seed, race, class_)
    (theirs,) = bridge.run_harness(
        [{"cmd": "play", "spec": spec, "ticks": ticks, "tasks": tasks}]
    )
    ours = bridge.play(DATA, spec, ticks, tasks)
    assert len(ours) == tasks
    assert_same_games(ours, theirs)


def assert_same_games(
    ours: list[dict[str, Any]], theirs: list[dict[str, Any]]
) -> None:
    assert len(ours) == len(theirs)
    for i, (mine, upstream) in enumerate(zip(ours, theirs)):
        if mine != upstream:
            previous = [snap["caption"] for snap in ours[max(0, i - 5) : i]]
            fields = {
                key: (mine[key], upstream[key])
                for key in mine
                if mine[key] != upstream[key]
            }
            pytest.fail(
                f"diverged at task {i} after {previous}:\n"
                + "\n".join(
                    f"  {key}:\n    pqcli:    {ours_value}\n"
                    f"    upstream: {theirs_value}"
                    for key, (ours_value, theirs_value) in fields.items()
                )
            )


# (tasks, ticks): stop right after a task, or in the middle of one
SAVE_POINTS = [(1000, 10**9), (10**9, 123457), (10**9, 1)]


@pytest.mark.parametrize("tasks,ticks", SAVE_POINTS)
def test_import_from_upstream_plays_on_identically(
    tasks: int, ticks: int
) -> None:
    spec = bridge.make_spec("import", "Eel Man", "Inner Mason")
    (game,) = bridge.run_harness(
        [{"cmd": "export", "spec": spec, "ticks": ticks, "tasks": tasks}]
    )
    (text, theirs) = bridge.run_harness(
        [
            {"cmd": "encode", "game": game},
            {"cmd": "resume", "game": game, "ticks": 10**9, "tasks": 1000},
        ]
    )
    player, warnings = import_game(decode(text), DATA)
    assert warnings == []
    ours = bridge.run(Simulation(player, DATA), 10**9, 1000)
    assert_same_games(ours, theirs)


@pytest.mark.parametrize("tasks,ticks", SAVE_POINTS)
def test_export_to_upstream_plays_on_identically(
    tasks: int, ticks: int
) -> None:
    spec = bridge.make_spec("export", "Panda Man", "Robot Monk")
    simulation = bridge.new_simulation(DATA, spec)
    bridge.run(simulation, ticks, tasks)
    text = encode(export_game(simulation.player, DATA))
    (game,) = bridge.run_harness([{"cmd": "decode", "text": text}])
    (theirs,) = bridge.run_harness(
        [{"cmd": "resume", "game": game, "ticks": 10**9, "tasks": 1000}]
    )
    ours = bridge.run(simulation, 10**9, 1000)
    assert_same_games(ours, theirs)
