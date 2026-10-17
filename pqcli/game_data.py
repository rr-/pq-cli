import json
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass, fields
from importlib import resources
from pathlib import Path
from typing import Any, cast

from pqcli.config import (
    Class,
    EquipmentPreset,
    Modifier,
    Monster,
    Race,
    StatType,
)

TARGET_PLACEHOLDER = "{target}"


class DataError(Exception):
    pass


@dataclass(frozen=True)
class GameData:
    spells: tuple[str, ...]
    offense_attrib: tuple[Modifier, ...]
    defense_attrib: tuple[Modifier, ...]
    offense_bad: tuple[Modifier, ...]
    defense_bad: tuple[Modifier, ...]
    shields: tuple[EquipmentPreset, ...]
    armors: tuple[EquipmentPreset, ...]
    weapons: tuple[EquipmentPreset, ...]
    specials: tuple[str, ...]
    item_attrib: tuple[str, ...]
    item_ofs: tuple[str, ...]
    boring_items: tuple[str, ...]
    monsters: tuple[Monster, ...]
    races: tuple[Race, ...]
    classes: tuple[Class, ...]
    titles: tuple[str, ...]
    impressive_titles: tuple[str, ...]
    combat_verbs: tuple[str, ...]


DATA_FILES = tuple(field.name for field in fields(GameData))


class _Context:
    def __init__(self, path: str) -> None:
        self.path = path

    def error(self, message: str) -> DataError:
        return DataError(f"{self.path}: {message}")


def _check_keys(
    ctx: _Context, where: str, obj: Any, keys: Sequence[str]
) -> dict[str, Any]:
    if not isinstance(obj, dict):
        raise ctx.error(f"{where} must be an object")
    missing = [key for key in keys if key not in obj]
    if missing:
        raise ctx.error(f"{where} is missing {', '.join(map(repr, missing))}")
    extra = [key for key in obj if key not in keys]
    if extra:
        raise ctx.error(f"{where} has unknown {', '.join(map(repr, extra))}")
    return obj


def _str(ctx: _Context, where: str, value: Any) -> str:
    if not isinstance(value, str):
        raise ctx.error(f"{where} must be a string")
    return value


def _int(ctx: _Context, where: str, value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ctx.error(f"{where} must be an integer")
    return value


def _stat(ctx: _Context, where: str, value: Any) -> StatType:
    _str(ctx, where, value)
    for stat in StatType:
        if value.lower() in (stat.value.lower(), stat.name):
            return stat
    allowed = ", ".join(stat.value for stat in StatType)
    raise ctx.error(f"{where}: unknown stat {value!r} (use one of {allowed})")


def _parse_str(ctx: _Context, where: str, item: Any) -> str:
    return _str(ctx, where, item)


def _parse_verb(ctx: _Context, where: str, item: Any) -> str:
    verb = _str(ctx, where, item)
    if TARGET_PLACEHOLDER not in verb:
        raise ctx.error(f"{where} must contain {TARGET_PLACEHOLDER}")
    return verb


def _parse_modifier(ctx: _Context, where: str, item: Any) -> Modifier:
    obj = _check_keys(ctx, where, item, ["name", "quality"])
    return Modifier(
        _str(ctx, f"{where}.name", obj["name"]),
        _int(ctx, f"{where}.quality", obj["quality"]),
    )


def _parse_preset(ctx: _Context, where: str, item: Any) -> EquipmentPreset:
    obj = _check_keys(ctx, where, item, ["name", "quality"])
    return EquipmentPreset(
        _str(ctx, f"{where}.name", obj["name"]),
        _int(ctx, f"{where}.quality", obj["quality"]),
    )


def _parse_monster(ctx: _Context, where: str, item: Any) -> Monster:
    obj = _check_keys(ctx, where, item, ["name", "level", "item"])
    loot = obj["item"]
    return Monster(
        _str(ctx, f"{where}.name", obj["name"]),
        _int(ctx, f"{where}.level", obj["level"]),
        None if loot is None else _str(ctx, f"{where}.item", loot),
    )


def _parse_attrs(ctx: _Context, where: str, value: Any) -> list[StatType]:
    if not isinstance(value, list):
        raise ctx.error(f"{where} must be a list of stats")
    return [_stat(ctx, f"{where}[{i}]", stat) for i, stat in enumerate(value)]


def _parse_race(ctx: _Context, where: str, item: Any) -> Race:
    obj = _check_keys(ctx, where, item, ["name", "attr"])
    return Race(
        _str(ctx, f"{where}.name", obj["name"]),
        _parse_attrs(ctx, f"{where}.attr", obj["attr"]),
    )


def _parse_class(ctx: _Context, where: str, item: Any) -> Class:
    obj = _check_keys(ctx, where, item, ["name", "attr"])
    return Class(
        _str(ctx, f"{where}.name", obj["name"]),
        _parse_attrs(ctx, f"{where}.attr", obj["attr"]),
    )


_PARSERS: dict[str, Callable[[_Context, str, Any], Any]] = {
    "spells": _parse_str,
    "offense_attrib": _parse_modifier,
    "defense_attrib": _parse_modifier,
    "offense_bad": _parse_modifier,
    "defense_bad": _parse_modifier,
    "shields": _parse_preset,
    "armors": _parse_preset,
    "weapons": _parse_preset,
    "specials": _parse_str,
    "item_attrib": _parse_str,
    "item_ofs": _parse_str,
    "boring_items": _parse_str,
    "monsters": _parse_monster,
    "races": _parse_race,
    "classes": _parse_class,
    "titles": _parse_str,
    "impressive_titles": _parse_str,
    "combat_verbs": _parse_verb,
}
assert set(_PARSERS) == set(DATA_FILES)


def _parse(name: str, path: str, text: str) -> tuple[Any, ...]:
    ctx = _Context(path)
    try:
        value = json.loads(text)
    except json.JSONDecodeError as ex:
        raise ctx.error(f"invalid JSON: {ex}") from ex
    if not isinstance(value, list):
        raise ctx.error("must be a list")
    if not value:
        raise ctx.error("must not be empty")
    parser = _PARSERS[name]
    return tuple(parser(ctx, f"[{i}]", item) for i, item in enumerate(value))


def _builtin_dir() -> Any:
    return resources.files("pqcli") / "data"


def _read_text(path: Any, display: str) -> str:
    try:
        return cast(str, path.read_text(encoding="utf-8"))
    except UnicodeDecodeError as ex:
        raise DataError(f"{display}: not valid UTF-8: {ex}") from ex
    except OSError as ex:
        raise DataError(f"{display}: cannot read: {ex}") from ex


def load_game_data(override_dir: Path | None = None) -> GameData:
    """Load the built-in word lists, replacing any that override_dir has.

    A missing override_dir is fine. Each <name>.json in it replaces the
    whole built-in list of that name.
    """
    overrides: set[str] = set()
    if override_dir is not None and override_dir.exists():
        if not override_dir.is_dir():
            raise DataError(f"{override_dir}: not a directory")
        for path in sorted(override_dir.glob("*.json")):
            if path.stem in DATA_FILES:
                overrides.add(path.stem)
            else:
                print(
                    f"pqcli: ignoring {path}: not a known data file "
                    f"(known: {', '.join(DATA_FILES)})",
                    file=sys.stderr,
                )

    values: dict[str, tuple[Any, ...]] = {}
    for name in DATA_FILES:
        if name in overrides:
            assert override_dir is not None
            source: Any = override_dir / f"{name}.json"
            display = str(source)
        else:
            source = _builtin_dir() / f"{name}.json"
            display = f"<built-in>/{name}.json"
        values[name] = _parse(name, display, _read_text(source, display))
    return GameData(**values)


def dump_builtin_data(target_dir: Path) -> list[Path]:
    """Copy the built-in data files to target_dir, never overwriting."""
    targets = [target_dir / f"{name}.json" for name in DATA_FILES]
    existing = [path for path in targets if path.exists()]
    if existing:
        raise DataError(
            "refusing to overwrite "
            + ", ".join(str(path) for path in existing)
        )
    target_dir.mkdir(parents=True, exist_ok=True)
    for name, path in zip(DATA_FILES, targets):
        source = _builtin_dir() / f"{name}.json"
        path.write_text(
            _read_text(source, f"<built-in>/{name}.json"), encoding="utf-8"
        )
    return targets
