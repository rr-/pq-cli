import datetime
import random
import typing as T
from dataclasses import dataclass

from pqcli.config import CLASSES, PRIME_STATS, RACES, Class, Race, Stat


def generate_name() -> str:
    parts = [
        "br|cr|dr|fr|gr|j|kr|l|m|n|pr||||r|sh|tr|v|wh|x|y|z".split("|"),
        "a|a|e|e|i|i|o|o|u|u|ae|ie|oo|ou".split("|"),
        "b|ck|d|g|k|m|n|p|t|v|x|z".split("|"),
    ]
    result = ""
    for i in range(6):
        result += random.choice(parts[i % 3])
    return result.title()


@dataclass
class Stats:
    def __init__(self):
        self.values = {stat: 0 for stat in Stat}

    def __iter__(self) -> T.Iterable[T.Tuple[Stat, int]]:
        return iter(self.values.items())

    def __setitem__(self, stat: Stat, value: int) -> None:
        self.values[stat] = value

    def __getitem__(self, stat: Stat) -> int:
        return self.values[stat]


@dataclass
class Player:
    name: str
    stats: Stats
    race: Race
    class_: Class
    birthday: datetime.datetime


class Roster:
    def __init__(self) -> None:
        self.players: T.List[Player] = []


class StatsBuilder:
    def __init__(self):
        self.history: T.List[Stats] = []

    def roll(self):
        stats = Stats()
        for stat in PRIME_STATS:
            stats[stat] = (
                3
                + random.randint(0, 5)
                + random.randint(0, 5)
                + random.randint(0, 5)
            )
        stats[Stat.hp_max] = random.randint(0, 7) + stats[Stat.condition] // 6
        stats[Stat.mp_max] = (
            random.randint(0, 7) + stats[Stat.intelligence] // 6
        )
        self.history.append(stats)
        return stats

    def unroll(self):
        self.history.pop()
        return self.history[-1]


def create_player(stats_builder: StatsBuilder) -> Player:
    now = datetime.datetime.now()
    random.seed(now)
    return Player(
        birthday=now,
        name=generate_name(),
        stats=stats_builder.roll(),
        race=random.choice(RACES),
        class_=random.choice(CLASSES),
    )
