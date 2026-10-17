import datetime
import typing as T
from pathlib import Path

from pqcli import random
from pqcli.config import StatType
from pqcli.game_data import load_game_data
from pqcli.mechanic import Player, Simulation, Stats, monster_task
from pqcli.random import Alea

STATS = {
    StatType.strength: 12,
    StatType.condition: 11,
    StatType.dexterity: 10,
    StatType.intelligence: 13,
    StatType.wisdom: 14,
    StatType.charisma: 9,
    StatType.hp_max: 6,
    StatType.mp_max: 5,
}


def run_trace(seed: str, ticks: int = 3000) -> T.List[str]:
    """Play a deterministic game and return everything that happened."""
    data = load_game_data()
    player = Player(
        name="Tester",
        birthday=datetime.datetime(2000, 1, 1),
        race=data.races[0],
        class_=data.classes[0],
        stats=Stats(dict(STATS)),
        rng=Alea(seed),
    )
    random.seed(seed)
    simulation = Simulation(player, data)

    lines: T.List[str] = []
    player.connect(
        "new_task",
        lambda: lines.append(f"task: {player.task.description}"),
    )
    for _ in range(ticks):
        simulation.tick(100000.0)

    with random.using(player.rng):
        # plot cinematics and quests are rare in a short run, so force them
        for _ in range(30):
            simulation.interplot_cinematic()
            simulation.complete_quest()
        lines.extend(f"queued: {task.description}" for task in player.queue)
        player.queue.clear()

        # high level monsters are unreachable in a short run
        for level in range(1, 100):
            task = monster_task(data, level, player.quest_book.monster)
            lines.append(f"monster: {task.description} {task.duration}")

    lines.append(f"level: {player.level}")
    lines.append(f"act: {player.quest_book.act}")
    lines.append(f"gold: {player.inventory.gold}")
    for stat, value in player.stats:
        lines.append(f"stat: {stat.value} {value}")
    for equipment_type, item in player.equipment:
        lines.append(f"equipment: {equipment_type.value} {item}")
    for inventory_item in player.inventory:
        lines.append(
            f"inventory: {inventory_item.name} {inventory_item.quantity}"
        )
    for spell in player.spell_book:
        lines.append(f"spell: {spell.name} {spell.level}")
    for quest in player.quest_book.quests:
        lines.append(f"quest: {quest}")
    return lines


SEEDS = ["alpha", "beta", "gamma"]
FIXTURES = Path(__file__).parent / "fixtures"


if __name__ == "__main__":
    # Re-record the parity fixtures. Only do this on purpose, when a change
    # is meant to alter gameplay.
    for seed in SEEDS:
        lines = run_trace(seed)
        (FIXTURES / f"parity_{seed}.txt").write_text("\n".join(lines) + "\n")
