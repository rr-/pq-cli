import enum
import typing as T
from dataclasses import dataclass


class StatType(enum.Enum):
    strength = "STR"
    condition = "CON"
    dexterity = "DEX"
    intelligence = "INT"
    wisdom = "WIS"
    charisma = "CHA"
    hp_max = "HP Max"
    mp_max = "MP Max"


class EquipmentType(enum.Enum):
    weapon = "Weapon"
    shield = "Shield"
    helm = "Helm"
    hauberk = "Hauberk"
    brassairts = "Brassairts"
    vambraces = "Vambraces"
    gauntlets = "Gauntlets"
    gambeson = "Gambeson"
    cuisses = "Cuisses"
    greaves = "Greaves"
    sollerets = "Sollerets"


PRIME_STATS = [
    StatType.strength,
    StatType.condition,
    StatType.dexterity,
    StatType.intelligence,
    StatType.wisdom,
    StatType.charisma,
]

ALL_STATS = PRIME_STATS + [StatType.hp_max, StatType.mp_max]

# The word lists live in pqcli/data/*.json (see pqcli.game_data).
# Saves pickle Monster, Race and Class instances by import path, so these
# classes must stay in this module.


@dataclass
class Modifier:
    name: str
    quality: int


@dataclass
class EquipmentPreset:
    name: str
    quality: int


@dataclass
class Monster:
    name: str
    level: int
    item: T.Optional[str]


@dataclass
class Race:
    name: str
    attr: T.List[StatType]


@dataclass
class Class:
    name: str
    attr: T.List[StatType]
