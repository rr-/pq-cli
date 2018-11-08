import argparse
import datetime
import logging
import sys
from pathlib import Path
from signal import SIG_DFL, SIGPIPE, signal

from pqcli import random
from pqcli.config import CLASSES, RACES
from pqcli.mechanic import (
    Player,
    Simulation,
    StatsBuilder,
    act_name,
    create_player,
    generate_name,
)
from pqcli.roster import Roster

signal(SIGPIPE, SIG_DFL)
logging.basicConfig(
    stream=sys.stdout, level=logging.DEBUG, format="%(message)s"
)


# make things predictable
SEED_A = 1_664_525
SEED_B = 2141
SEED_C = 1_013_904_223


def custom_random(num: int) -> int:
    global SEED_A, SEED_B, SEED_C
    SEED_B = (SEED_A * SEED_B + SEED_C) % 0x100000000
    return SEED_B % num


random.below = custom_random


def character_sheet(player: Player) -> None:
    print(f"{player.name} the {player.race.name}")
    print(f"Level {player.level} {player.class_.name}")
    print(f"Plot stage: {act_name(player.quest_book.act)}")
    print(f"Quest: {player.quest_book.current_quest}")
    print()
    print("Stats:")
    for stat, value in player.stats:
        print(f"  {stat.value}: {value}")
    print()
    print(f"Equipment (best: {player.equipment.best}):")
    for equipment, item_name in player.equipment:
        print(f"  {equipment.value}: {item_name}")
    print()
    print("Spell Book:")
    for spell in player.spell_book:
        print(f"  {spell.name}: {spell.level}")
    print()
    print("Inventory:")
    print(f"  Gold: {player.inventory.gold}")
    for item in player.inventory:
        print(f"  {item.name}: {item.quantity}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("-r", "--roster", type=Path)
    parser.add_argument("-l", "--max-level", type=int, default=5)
    return parser.parse_args()


def random_player() -> Player:
    return create_player(
        stats=StatsBuilder().roll(),
        name=generate_name(),
        race=random.choice(RACES),
        class_=random.choice(CLASSES),
    )


def main() -> None:
    args = parse_args()

    if args.roster:
        roster = Roster.load(args.roster)
        if not roster.players:
            roster.players.append(random_player())
            roster.save()
        player = roster.players[0]
    else:
        roster = None
        player = random_player()

    start = datetime.datetime.now()
    elapsed = 0
    last_level = 0
    simulation = Simulation(player)
    try:
        while True:
            if player.level != last_level:
                last_level = player.level
                character_sheet(player)
                if player.level >= args.max_level:
                    break
            simulation.tick()
            elapsed += 100
    finally:
        print("real time: ", (datetime.datetime.now() - start))
        print("virtual time: ", datetime.timedelta(milliseconds=elapsed))
        if roster:
            roster.save()


if __name__ == "__main__":
    main()
