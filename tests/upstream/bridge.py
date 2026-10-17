"""Run upstream's JS and pqcli side by side, producing comparable data."""

import datetime
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any, cast

from pqcli.config import EquipmentType, Monster, StatType
from pqcli.game_data import GameData
from pqcli.lingo import to_roman
from pqcli.mechanic import (
    BaseTask,
    Player,
    PlotTask,
    Simulation,
    Stats,
)
from pqcli.random import Alea, RngState

from .fetch import cache_dir, is_fetched

HARNESS = Path(__file__).parent / "harness.js"

# pqcli data file -> upstream K.* list
LISTS = {
    "spells": "Spells",
    "offense_attrib": "OffenseAttrib",
    "defense_attrib": "DefenseAttrib",
    "offense_bad": "OffenseBad",
    "defense_bad": "DefenseBad",
    "shields": "Shields",
    "armors": "Armors",
    "weapons": "Weapons",
    "specials": "Specials",
    "item_attrib": "ItemAttrib",
    "item_ofs": "ItemOfs",
    "boring_items": "BoringItems",
    "monsters": "Monsters",
    "races": "Races",
    "classes": "Klasses",
    "titles": "Titles",
    "impressive_titles": "ImpressiveTitles",
}


def unavailable_reason() -> str | None:
    if shutil.which("node") is None:
        return "node is not installed"
    if not is_fetched(cache_dir()):
        return (
            f"upstream is not fetched into {cache_dir()}; "
            "run `just fetch-upstream`"
        )
    return None


def run_harness(requests: list[dict[str, Any]]) -> list[Any]:
    result = subprocess.run(
        ["node", str(HARNESS), str(cache_dir())],
        input=json.dumps(requests),
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


def encode_list(name: str, data: GameData) -> list[str]:
    """Write a pqcli word list the way upstream's config.js spells it."""
    items: list[Any] = list(getattr(data, name))
    if name in {"offense_attrib", "defense_attrib"}:
        return [f"{item.name}|{item.quality:+d}" for item in items]
    if name in {"offense_bad", "defense_bad", "shields", "armors", "weapons"}:
        return [f"{item.name}|{item.quality}" for item in items]
    if name == "monsters":
        return [encode_monster(item) for item in items]
    if name in {"races", "classes"}:
        return [
            item.name + "|" + ",".join(stat.value for stat in item.attr)
            for item in items
        ]
    return items


def encode_monster(monster: Monster | None) -> str:
    if monster is None:
        return ""
    return f"{monster.name}|{monster.level}|{monster.item or '*'}"


def make_spec(seed: str, race: str, class_: str) -> dict[str, Any]:
    rng = Alea(seed)
    stats = {}
    for stat in ["STR", "CON", "DEX", "INT", "WIS", "CHA"]:
        stats[stat] = 3 + sum(rng.uint32() % 6 for _ in range(3))
    stats["HP Max"] = rng.uint32() % 8 + stats["CON"] // 6
    stats["MP Max"] = rng.uint32() % 8 + stats["INT"] // 6
    return {
        "name": "Tester",
        "race": race,
        "class": class_,
        "stats": stats,
        "seed": list(rng.state()),
    }


def _queue_entry(task: BaseTask) -> str:
    kind = "plot" if isinstance(task, PlotTask) else "task"
    text = "Loading" if isinstance(task, PlotTask) else task.description
    return f"{kind}|{task.duration // 1000}|{text}"


def snapshot(player: Player) -> dict[str, Any]:
    assert player.task is not None
    bars = {
        "ExpBar": player.exp_bar,
        "PlotBar": player.quest_book.plot_bar,
        "QuestBar": player.quest_book.quest_bar,
        "EncumBar": player.inventory.encum_bar,
        "TaskBar": player.task_bar,
    }
    return {
        "caption": player.task.description,
        "level": player.level,
        "act": player.quest_book.act,
        "bars": {name: [bar.position, bar.max_] for name, bar in bars.items()},
        "stats": {stat.value: player.stats[stat] for stat in StatType},
        "equipment": {
            kind.value: player.equipment[kind] or "" for kind in EquipmentType
        },
        "gold": player.inventory.gold,
        "inventory": [[item.name, item.quantity] for item in player.inventory],
        "spells": [
            [spell.name, to_roman(spell.level)] for spell in player.spell_book
        ],
        "quests": list(player.quest_book.quests),
        "questmonster": encode_monster(player.quest_book.monster),
        "queue": [_queue_entry(task) for task in player.queue],
        "rng": list(player.rng.state()),
    }


def play(
    data: GameData, spec: dict[str, Any], ticks: int, tasks: int
) -> list[dict[str, Any]]:
    """Play pqcli the way the harness plays upstream: 100 ms ticks."""
    race = next(race for race in data.races if race.name == spec["race"])
    class_ = next(c for c in data.classes if c.name == spec["class"])
    seed = cast(RngState, tuple(spec["seed"]))
    player = Player(
        name=spec["name"],
        birthday=datetime.datetime(2000, 1, 1),
        race=race,
        class_=class_,
        stats=Stats({StatType(k): v for k, v in spec["stats"].items()}),
        rng=Alea.from_state(seed),
    )
    simulation = Simulation(player, data)
    simulation.tick(0)  # sets up the Prologue, as upstream's sold() does
    snapshots = []
    for _ in range(ticks):
        completing = player.task_bar.done
        simulation.tick(100)
        if completing:
            snapshots.append(snapshot(player))
            if len(snapshots) >= tasks:
                break
    return snapshots
