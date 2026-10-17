"""Import and export Progress Quest web saves (.pqw files).

A .pqw file is base64 of one character's JSON, as the web version's roster
page downloads it. Characters keep their generator state both ways, so they
carry on exactly as they would have where they came from.
"""

import base64
import binascii
import copy
import datetime
import json
from pathlib import Path
from typing import Any, cast

from pqcli.config import Class, EquipmentType, Monster, Race, StatType
from pqcli.game_data import GameData
from pqcli.lingo import act_name, to_arabic, to_roman
from pqcli.mechanic import (
    BaseTask,
    BuyTask,
    HeadingToKillingFieldsTask,
    HeadingToMarketTask,
    InventoryItem,
    KillTask,
    LoadingTask,
    Player,
    PlotTask,
    RegularTask,
    SellTask,
    Simulation,
    Spell,
    Stats,
)
from pqcli.random import Alea, RngState

# Spells upstream renamed; its loader merges old saves the same way.
SPELL_RENAMES = [
    ("Innoculate", "Inoculate"),
    ("Tonsilectomy", "Tonsillectomy"),
]

# Fields of the web save that pqcli has no use for.
ONLINE_FIELDS = ("online", "guild", "motto")

LOADING_CAPTION = "Loading...."


class PqwError(Exception):
    pass


def decode(text: str) -> dict[str, Any]:
    """Turn the contents of a .pqw file into the web save's game object."""
    try:
        raw = base64.b64decode("".join(text.split()), validate=True)
    except (binascii.Error, ValueError) as ex:
        raise PqwError(f"not a .pqw file: {ex}") from ex
    try:
        decoded = raw.decode("utf-8")
    except UnicodeDecodeError:
        # saves from before 2022 were base64 of the raw JS string
        decoded = raw.decode("latin-1")
    try:
        game = json.loads(decoded)
    except json.JSONDecodeError as ex:
        raise PqwError(f"not a .pqw file: {ex}") from ex
    if not isinstance(game, dict) or "Traits" not in game:
        raise PqwError("not a .pqw file: no character in it")
    return game


def encode(game: dict[str, Any]) -> str:
    """Turn a web save's game object into the contents of a .pqw file."""
    text = json.dumps(game, ensure_ascii=False, separators=(",", ":"))
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


def _field(game: dict[str, Any], *path: str | int) -> Any:
    value: Any = game
    for key in path:
        try:
            value = value[key]
        except (KeyError, IndexError, TypeError) as ex:
            name = ".".join(map(str, path))
            raise PqwError(f"missing field {name}") from ex
    return value


def _int(game: dict[str, Any], *path: str | int) -> int:
    value = _field(game, *path)
    try:
        return int(value)
    except (TypeError, ValueError) as ex:
        name = ".".join(map(str, path))
        raise PqwError(f"field {name} is not a number: {value!r}") from ex


def _bar(game: dict[str, Any], name: str) -> tuple[int, float]:
    position = _field(game, name, "position")
    if not isinstance(position, int | float):
        raise PqwError(f"field {name}.position is not a number")
    return _int(game, name, "max"), position


def _parse_monster(text: str) -> Monster | None:
    if not text:
        return None
    parts = text.split("|")
    if len(parts) != 3:
        raise PqwError(f"cannot read monster {text!r}")
    name, level, item = parts
    try:
        return Monster(name, int(level), None if item == "*" else item)
    except ValueError as ex:
        raise PqwError(f"cannot read monster {text!r}") from ex


def _encode_monster(monster: Monster) -> str:
    return f"{monster.name}|{monster.level}|{monster.item or '*'}"


def _parse_task(game: dict[str, Any]) -> BaseTask:
    kind = str(_field(game, "task"))
    caption = str(_field(game, "kill"))
    duration = _bar(game, "TaskBar")[0]
    if kind.startswith("kill|"):
        monster = _parse_monster(kind.removeprefix("kill|"))
        return KillTask(caption.removesuffix("..."), duration, monster)
    if caption == LOADING_CAPTION:
        return LoadingTask("Loading", duration)
    task_class: type[BaseTask] = {
        "buying": BuyTask,
        "market": HeadingToMarketTask,
        "sell": SellTask,
        "heading": HeadingToKillingFieldsTask,
        "": RegularTask,
    }.get(kind, RegularTask)
    return task_class(caption.removesuffix("..."), duration)


def _encode_task(task: BaseTask) -> tuple[str, str]:
    if isinstance(task, LoadingTask):
        return "", LOADING_CAPTION
    caption = task.description + "..."
    if isinstance(task, KillTask):
        monster = task.monster or Monster("", 0, None)
        return "kill|" + _encode_monster(monster), caption
    for task_class, kind in [
        (BuyTask, "buying"),
        (HeadingToMarketTask, "market"),
        (SellTask, "sell"),
        (HeadingToKillingFieldsTask, "heading"),
    ]:
        if isinstance(task, task_class):
            return kind, caption
    return "", caption


def _parse_queue_entry(entry: Any) -> RegularTask:
    parts = str(entry).split("|", 2)
    if len(parts) != 3 or parts[0] not in {"task", "plot"}:
        raise PqwError(f"cannot read queued task {entry!r}")
    try:
        duration = int(parts[1]) * 1000
    except ValueError as ex:
        raise PqwError(f"cannot read queued task {entry!r}") from ex
    if parts[0] == "plot":
        # renamed after the act it starts once it comes up
        return PlotTask("Loading", duration)
    return RegularTask(parts[2], duration)


def _encode_queue_entry(task: BaseTask) -> str:
    seconds = task.duration // 1000
    if isinstance(task, PlotTask):
        return f"plot|{seconds}|Loading"
    return f"task|{seconds}|{task.description}"


def _parse_spells(game: dict[str, Any]) -> list[Spell]:
    rows = [(str(row[0]), str(row[1])) for row in _field(game, "Spells")]
    levels = {name: to_arabic(roman) for name, roman in rows}
    spells = []
    for name, _roman in rows:
        renamed = dict(SPELL_RENAMES).get(name)
        if renamed is not None:
            levels[renamed] = levels.get(renamed, 0) + levels[name]
            name = renamed
        elif any(new == name and old in levels for old, new in SPELL_RENAMES):
            continue  # merged into the old spell's place
        spells.append(Spell(name, levels[name]))
    return spells


def _find_by_name(
    items: tuple[Race, ...] | tuple[Class, ...], name: str
) -> Race | Class | None:
    return next((item for item in items if item.name == name), None)


def import_game(
    game: dict[str, Any], data: GameData
) -> tuple[Player, list[str]]:
    """Build a pqcli character from a web save, plus any warnings."""
    warnings = []
    for field in ONLINE_FIELDS:
        if game.get(field):
            warnings.append(f"dropped {field!r}: pqcli plays offline only")

    name = str(_field(game, "Traits", "Name"))
    race_name = str(_field(game, "Traits", "Race"))
    class_name = str(_field(game, "Traits", "Class"))
    race = _find_by_name(data.races, race_name) or Race(race_name, [])
    class_ = _find_by_name(data.classes, class_name) or Class(class_name, [])

    stats = Stats({stat: _int(game, "Stats", stat.value) for stat in StatType})
    seed = _field(game, "seed")
    if not (isinstance(seed, list) and len(seed) == 4):
        raise PqwError("field seed is not a generator state")
    stamp = game.get("birthstamp")
    birthday = (
        datetime.datetime.fromtimestamp(stamp / 1000)
        if isinstance(stamp, int | float)
        else datetime.datetime.now()
    )

    player = Player(
        name=name,
        birthday=birthday,
        race=cast(Race, race),
        class_=cast(Class, class_),
        stats=stats,
        rng=Alea.from_state(cast(RngState, tuple(seed))),
    )
    player.level = _int(game, "Traits", "Level")
    player.elapsed = float(game.get("elapsed", 0)) * 1000

    player.exp_bar.reset(*_bar(game, "ExpBar"))
    player.task_bar.reset(*_bar(game, "TaskBar"))
    player.quest_book.plot_bar.reset(*_bar(game, "PlotBar"))
    player.quest_book.quest_bar.reset(*_bar(game, "QuestBar"))

    player.quest_book._act = _int(game, "act")
    player.quest_book._quests = [str(q) for q in _field(game, "Quests")]
    player.quest_book.monster = _parse_monster(
        str(game.get("questmonster", ""))
    )

    for kind in EquipmentType:
        item = str(_field(game, "Equips").get(kind.value, ""))
        if item:
            player.equipment.put(kind, item)
    player.equipment.best = str(game.get("bestequip", player.equipment.best))

    rows = _field(game, "Inventory")
    if not rows or rows[0][0] != "Gold":
        raise PqwError("field Inventory does not start with Gold")
    player.inventory._gold = _int(game, "Inventory", 0, 1)
    player.inventory._items = [
        InventoryItem(str(row[0]), int(row[1])) for row in rows[1:]
    ]
    player.inventory.encum_bar.reset(*_bar(game, "EncumBar"))

    player.spell_book._spells = _parse_spells(game)

    player.task = _parse_task(game)
    player.queue = [_parse_queue_entry(e) for e in _field(game, "queue")]
    return player, warnings


def export_game(player: Player, data: GameData) -> dict[str, Any]:
    """Build a web save from a pqcli character."""
    if player.task is None:
        # never played: set up the Prologue first, on a copy
        player = copy.deepcopy(player)
        Simulation(player, data).tick(0)
    assert player.task is not None

    seed = list(player.rng.state())
    birthstamp = int(player.birthday.timestamp() * 1000)
    now = datetime.datetime.now()
    kind, caption = _encode_task(player.task)
    best_stat = player.stats.best_prime
    best_spell = player.spell_book.best

    quest_monster = player.quest_book.monster
    # upstream picks the quest monster by its index in the monster list
    quest_monster_index = (
        data.monsters.index(quest_monster)
        if quest_monster in data.monsters
        else 0
    )

    def bar(position: float, max_: int) -> dict[str, float]:
        return {"position": position, "max": max_}

    return {
        "Traits": {
            "Name": player.name,
            "Race": player.race.name,
            "Class": player.class_.name,
            "Level": player.level,
        },
        "dna": seed,
        "seed": seed,
        "birthday": player.birthday.strftime("%a %b %d %Y %H:%M:%S"),
        "birthstamp": birthstamp,
        "date": now.strftime("%a %b %d %Y %H:%M:%S"),
        "stamp": int(now.timestamp() * 1000),
        "Stats": {stat.value: player.stats[stat] for stat in StatType},
        "beststat": f"{best_stat.value} {player.stats[best_stat]}",
        "task": kind,
        "tasks": 0,
        "elapsed": int(player.elapsed // 1000),
        "bestequip": player.equipment.best,
        "Equips": {
            kind.value: player.equipment[kind] or "" for kind in EquipmentType
        },
        "Inventory": [["Gold", player.inventory.gold]]
        + [[item.name, item.quantity] for item in player.inventory],
        "Spells": [
            [spell.name, to_roman(spell.level)] for spell in player.spell_book
        ],
        "bestspell": (
            f"{best_spell.name} {to_roman(best_spell.level)}"
            if best_spell
            else ""
        ),
        "act": player.quest_book.act,
        "bestplot": act_name(player.quest_book.act),
        "Quests": list(player.quest_book.quests),
        "bestquest": player.quest_book.current_quest or "",
        "questmonster": (
            _encode_monster(quest_monster) if quest_monster else ""
        ),
        "questmonsterindex": quest_monster_index,
        "kill": caption,
        "ExpBar": bar(player.exp_bar.position, player.exp_bar.max_),
        "EncumBar": bar(
            player.inventory.encum_bar.position,
            player.inventory.encum_bar.max_,
        ),
        "PlotBar": bar(
            player.quest_book.plot_bar.position,
            player.quest_book.plot_bar.max_,
        ),
        "QuestBar": bar(
            player.quest_book.quest_bar.position,
            player.quest_book.quest_bar.max_,
        ),
        "TaskBar": bar(player.task_bar.position, player.task_bar.max_),
        "queue": [_encode_queue_entry(task) for task in player.queue],
    }


def read_file(path: Path, data: GameData) -> tuple[Player, list[str]]:
    """Import the character in a .pqw file, plus any warnings."""
    try:
        text = path.read_text(encoding="ascii", errors="replace")
    except OSError as ex:
        raise PqwError(f"cannot read {path}: {ex.strerror}") from ex
    return import_game(decode(text), data)


def write_file(player: Player, path: Path, data: GameData) -> None:
    """Export a character to a .pqw file, never overwriting one."""
    text = encode(export_game(player, data))
    try:
        with path.open("x", encoding="ascii") as handle:
            handle.write(text)
    except FileExistsError as ex:
        raise PqwError(f"{path} already exists") from ex
    except OSError as ex:
        raise PqwError(f"cannot write {path}: {ex.strerror}") from ex


def default_file_name(player: Player) -> str:
    # the web version names its downloads the same way
    return f"{player.name}.pqw"
