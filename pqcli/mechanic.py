import datetime
import functools
import itertools
import logging
import math
from collections import defaultdict
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
from typing import Any, cast

from pqcli import random
from pqcli.config import (
    PRIME_STATS,
    Class,
    EquipmentPreset,
    EquipmentType,
    Modifier,
    Monster,
    Race,
    StatType,
)
from pqcli.game_data import TARGET_PLACEHOLDER, GameData
from pqcli.lingo import (
    act_name,
    big,
    definite,
    generate_name,
    indefinite,
    plural,
    sick,
    special,
    young,
)
from pqcli.random import Alea, RngState

logger = logging.getLogger(__name__)


_SIGNALS: dict[tuple["SignalMixin", str], list[Callable[..., Any]]] = (
    defaultdict(list)
)


class SignalMixin:
    def emit(self, signal_name: str, *user_data: Any) -> None:
        for callback in _SIGNALS[self, signal_name]:
            callback(*user_data)

    def connect(self, signal_name: str, callback: Callable[..., Any]) -> None:
        _SIGNALS[self, signal_name].append(callback)

    def disconnect(
        self, signal_name: str, callback: Callable[..., Any]
    ) -> None:
        try:
            idx = _SIGNALS[self, signal_name].index(callback)
        except ValueError:
            return
        del _SIGNALS[self, signal_name][idx]


def level_up_time(level: int) -> int:
    # seconds: 20 minutes for level 1, exponential increase after that.
    # floor(x + 0.5) mirrors JS Math.round, unlike Python's round().
    return math.floor((20 + 1.15**level) * 60 + 0.5)


class Bar(SignalMixin):
    signals = ["change"]

    def __init__(self, max_: int, position: float = 0.0) -> None:
        self._position = position
        self._max = max_
        self.emit("change")

    def reset(self, new_max: int, position: float = 0.0) -> None:
        if not math.isclose(new_max, self._max) or not math.isclose(
            position, self._position
        ):
            self._max = new_max
            self._position = position
            self.emit("change")

    def increment(self, inc: float) -> None:
        self.reposition(self._position + inc)

    @property
    def max_(self) -> int:
        return self._max

    @property
    def position(self) -> float:
        return self._position

    @property
    def done(self) -> bool:
        return self._position >= self.max_

    def reposition(self, new_pos: float) -> None:
        old_pos = self._position
        new_pos = float(min(new_pos, self._max))
        self._position = new_pos
        if not math.isclose(new_pos, old_pos):
            self.emit("change")


class Stats(SignalMixin):
    signals = ["change"]

    def __init__(self, values: dict[StatType, int]) -> None:
        self._values = values

    def __iter__(self) -> Iterator[tuple[StatType, int]]:
        return iter(self._values.items())

    def __getitem__(self, stat: StatType) -> int:
        return self._values[stat]

    @property
    def best(self) -> StatType:
        return max(self, key=lambda kv: kv[1])[0]

    @property
    def best_prime(self) -> StatType:
        return max(
            (kv for kv in self if kv[0] in PRIME_STATS), key=lambda kv: kv[1]
        )[0]

    def increment(self, stat: StatType, qty: int = 1) -> None:
        self._values[stat] += qty
        logger.info("Increased %s to %d", stat.value, self[stat])
        self.emit("change")


class QuestBook(SignalMixin):
    signals = ["start_act", "start_quest"]

    def __init__(self) -> None:
        self._quests: list[str] = []
        self._act = 0
        self.plot_bar = Bar(max_=1)
        self.quest_bar = Bar(max_=1)
        self.monster: Monster | None = None

    @property
    def act(self) -> int:
        return self._act

    @property
    def quests(self) -> list[str]:
        return self._quests

    @property
    def current_quest(self) -> str | None:
        if self._quests:
            return self._quests[-1]
        return None

    def increment_act(self) -> None:
        self._act += 1
        self.emit("start_act", self._act)

    def add_quest(self, name: str) -> None:
        logger.info("Commencing quest: %s", name)
        self._quests = self._quests[-99:]
        self._quests.append(name)


@dataclass
class InventoryItem:
    name: str
    quantity: int


class Inventory(SignalMixin):
    signals = ["gold_change", "item_add", "item_change", "item_del"]

    def __init__(self, capacity: int = 0) -> None:
        self._gold = 0
        self._items: list[InventoryItem] = []
        self.encum_bar = Bar(max_=capacity)

    @property
    def gold(self) -> int:
        return self._gold

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self) -> Iterator[InventoryItem]:
        return iter(self._items)

    def __getitem__(self, idx: int) -> InventoryItem:
        return self._items[idx]

    def add_gold(self, quantity: int) -> None:
        logger.info(
            "%s %s",
            "Spent" if quantity < 0 else "Got paid",
            indefinite("gold piece", abs(quantity)),
        )
        self._gold += quantity
        self.emit("gold_change")

    def pop(self, index: int) -> None:
        item = self._items[index]
        logger.info("Lost %s", indefinite(item.name, item.quantity))
        self._items.pop(index)
        self.sync_encumbrance()
        self.emit("item_del", item)

    def add(self, item_name: str, quantity: int) -> None:
        logger.info("Gained %s", indefinite(item_name, quantity))
        for item in self._items:
            if item.name == item_name:
                item.quantity += quantity
                self.emit("item_change", item)
                break
        else:
            item = InventoryItem(name=item_name, quantity=quantity)
            self._items.append(item)
            self.emit("item_add", item)
        self.sync_encumbrance()

    def sync_encumbrance(self) -> None:
        self.encum_bar.reposition(sum(item.quantity for item in self._items))

    def set_capacity(self, capacity: int) -> None:
        self.encum_bar.reset(capacity, self.encum_bar.position)


class Equipment(SignalMixin):
    signals = ["change"]

    def __init__(self) -> None:
        self._items: dict[EquipmentType, str] = {
            EquipmentType.weapon: "Sharp Rock",
            EquipmentType.hauberk: "-3 Burlap",
        }
        self.best = self[EquipmentType.weapon]

    def __iter__(self) -> Iterator[tuple[EquipmentType, str]]:
        return iter(self._items.items())

    def __getitem__(self, equipment_type: EquipmentType) -> str | None:
        return self._items.get(equipment_type, None)

    def put(self, equipment_type: EquipmentType, item_name: str) -> None:
        self._items[equipment_type] = item_name
        self.emit("change", equipment_type, item_name)
        self.best = item_name + (
            " " + equipment_type.value
            if equipment_type
            not in {EquipmentType.weapon, EquipmentType.shield}
            else ""
        )


@dataclass
class Spell:
    name: str
    level: int


class SpellBook(SignalMixin):
    signals = ["add", "change"]

    def __init__(self) -> None:
        self._spells: list[Spell] = []

    def __iter__(self) -> Iterator[Spell]:
        return iter(self._spells)

    def __bool__(self) -> bool:
        return bool(self._spells)

    def __len__(self) -> int:
        return len(self._spells)

    def add(self, spell_name: str, level: int) -> None:
        for spell in self._spells:
            if spell.name == spell_name:
                spell.level += level
                logger.info("Learned %s at level %d", spell_name, spell.level)
                self.emit("change", spell)
                break
        else:
            spell = Spell(name=spell_name, level=level)
            self._spells.append(spell)
            logger.info("Learned %s at level %d", spell.name, spell.level)
            self.emit("add", spell)

    @property
    def best(self) -> Spell | None:
        if not self._spells:
            return None
        return max(self._spells, key=lambda spell: spell.level)


@dataclass
class BaseTask:
    description: str
    duration: int


@dataclass
class KillTask(BaseTask):
    monster: Monster | None = None


class BuyTask(BaseTask):
    pass


class HeadingToKillingFieldsTask(BaseTask):
    pass


class HeadingToMarketTask(BaseTask):
    pass


class SellTask(BaseTask):
    pass


class RegularTask(BaseTask):
    pass


class PlotTask(RegularTask):
    pass


class LoadingTask(RegularTask):
    pass


class Player(SignalMixin):
    signals = ["new_task", "level_up"]

    def __init__(
        self,
        name: str,
        birthday: datetime.datetime,
        race: Race,
        class_: Class,
        stats: Stats,
        rng: Alea | None = None,
    ) -> None:
        self.name: str = name
        self.birthday: datetime.datetime = birthday
        self.race: Race = race
        self.class_: Class = class_
        self.stats: Stats = stats
        self.rng: Alea = rng or Alea()
        self.elapsed = 0.0

        self.exp_bar = Bar(max_=level_up_time(1))
        self.level = 1

        self.quest_book = QuestBook()
        self.inventory = Inventory(capacity=10 + self.stats[StatType.strength])
        self.equipment = Equipment()
        self.spell_book = SpellBook()

        self.task_bar = Bar(max_=1)
        self.task: BaseTask | None = None
        self.queue: list[BaseTask] = []

    def __setstate__(self, obj: Any) -> None:
        self.__dict__.update(obj)
        self.elapsed = obj.get("elapsed", 0.0)
        if "rng" not in obj:
            self.rng = Alea()

    def set_task(self, task: BaseTask) -> None:
        self.task = task
        self.task_bar.reset(task.duration)
        logger.info("%s...", task.description)
        self.emit("new_task")

    def equip_price(self) -> int:
        return 5 * (self.level**2) + 10 * self.level + 20

    def level_up(self, data: GameData) -> None:
        self.level += 1
        logger.info("Leveled up to level %d!", self.level)
        self.stats.increment(
            StatType.hp_max,
            self.stats[StatType.condition] // 3 + 1 + random.below(4),
        )
        self.stats.increment(
            StatType.mp_max,
            self.stats[StatType.intelligence] // 3 + 1 + random.below(4),
        )
        self.win_stat()
        self.win_stat()
        self.win_spell(data)
        self.exp_bar.reset(level_up_time(self.level))
        self.emit("level_up")

    def win_stat(self) -> bool:
        chosen_stat: StatType | None = None

        if random.odds(1, 2):
            chosen_stat = random.choice(list(StatType))
        else:
            # favor the best stat so it will tend to clump
            t = sum(self.stats[stat] ** 2 for stat in PRIME_STATS)
            t = random.below(t)
            chosen_stat = None
            for stat in PRIME_STATS:
                chosen_stat = stat
                t -= self.stats[stat] ** 2
                if t < 0:
                    break

        assert chosen_stat is not None
        self.stats.increment(chosen_stat)
        if chosen_stat == StatType.strength:
            self.inventory.set_capacity(10 + self.stats[StatType.strength])
        return True

    def win_spell(self, data: GameData) -> None:
        spells = data.spells
        self.spell_book.add(
            spells[
                random.below_low(
                    min(self.stats[StatType.wisdom] + self.level, len(spells))
                )
            ],
            1,
        )

    def win_equipment(self, data: GameData) -> None:
        choice = random.choice(list(EquipmentType))

        stuff: Sequence[EquipmentPreset]
        better: Sequence[Modifier]
        worse: Sequence[Modifier]

        if choice == EquipmentType.weapon:
            stuff = data.weapons
            better = data.offense_attrib
            worse = data.offense_bad
        else:
            stuff = (
                data.shields if choice == EquipmentType.shield else data.armors
            )
            better = data.defense_attrib
            worse = data.defense_bad

        equipment = pick_equipment(stuff, self.level)
        name = equipment.name
        plus = self.level - equipment.quality
        if plus < 0:
            modifier_pool = worse
        else:
            modifier_pool = better
        count = 0
        while count < 2 and plus:
            modifier = random.choice(modifier_pool)
            if modifier.name in name:
                break  # no repeats
            if abs(plus) < abs(modifier.quality):
                break  # too much
            name = modifier.name + " " + name
            plus -= modifier.quality
            count += 1

        if plus < 0:
            name = f"{plus} {name}"
        if plus > 0:
            name = f"+{plus} {name}"

        logger.info("Gained %s %s", name, choice.value)
        self.equipment.put(choice, name)

    def win_item(self, data: GameData) -> None:
        # Past 250 rows, sometimes add one more of something already carried.
        # Upstream counts the Gold row too, and picking it yields 1 gold.
        rows = len(self.inventory) + 1
        if max(250, random.below(999)) < rows:
            index = random.below(rows)
            if index == 0:
                self.inventory.add_gold(1)
            else:
                self.inventory.add(self.inventory[index - 1].name, 1)
        else:
            self.inventory.add(special_item(data), 1)


class Simulation:
    def __init__(self, player: Player, data: GameData) -> None:
        self.player = player
        self.data = data
        self.last_tick = datetime.datetime.now()

    def tick(self, elapsed: float = 100.0) -> None:
        # each character plays on its own generator, saved along with it
        with random.using(self.player.rng):
            self._tick(elapsed)

    def _tick(self, elapsed: float) -> None:
        self.player.elapsed += elapsed

        if self.player.task is None:
            self.player.set_task(LoadingTask("Loading", 2000))
            self.player.queue += [
                RegularTask(
                    "Experiencing an enigmatic and foreboding night vision",
                    10000,
                ),
                RegularTask(
                    "Much is revealed about that wise old bastard "
                    "you'd underestimated",
                    6000,
                ),
                RegularTask(
                    "A shocking series of events leaves you "
                    "alone and bewildered, but resolute",
                    6000,
                ),
                RegularTask(
                    "Drawing upon an unrealized reserve of determination, "
                    "you set out on a long and dangerous journey",
                    4000,
                ),
                PlotTask(f"Loading {act_name(1)}", 2000),
            ]
            self.player.quest_book.plot_bar.reset(26)
            return

        if not self.player.task_bar.done:
            self.player.task_bar.increment(elapsed)
            return

        # gain XP / level up
        gain = self.player.task and isinstance(self.player.task, KillTask)
        if gain:
            if self.player.exp_bar.done:
                self.player.level_up(self.data)
            else:
                self.player.exp_bar.increment(self.player.task_bar.max_ / 1000)

        # advance quest
        if gain and self.player.quest_book.act >= 1:
            if (
                self.player.quest_book.quest_bar.done
                or self.player.quest_book.current_quest is None
            ):
                self.complete_quest()
            else:
                self.player.quest_book.quest_bar.increment(
                    self.player.task_bar.max_ / 1000
                )

        # advance plot
        if gain:
            if self.player.quest_book.plot_bar.done:
                self.interplot_cinematic()
            else:
                self.player.quest_book.plot_bar.increment(
                    self.player.task_bar.max_ / 1000
                )
        elif self.player.quest_book.act == 0 and not isinstance(
            self.player.task, LoadingTask | PlotTask
        ):
            # the Prologue story tasks fill the plot bar
            self.player.quest_book.plot_bar.increment(
                self.player.task_bar.max_ / 1000
            )

        self.dequeue()

    def dequeue(self) -> None:
        while self.player.task_bar.done:
            if isinstance(self.player.task, KillTask):
                if (
                    self.player.task.monster is None
                    or self.player.task.monster.item is None
                ):
                    # npc
                    self.player.win_item(self.data)
                elif self.player.task.monster.item:
                    self.player.inventory.add(
                        (
                            self.player.task.monster.name
                            + " "
                            + self.player.task.monster.item
                        ).lower(),
                        1,
                    )

            elif isinstance(self.player.task, BuyTask):
                # buy some equipment
                self.player.inventory.add_gold(-self.player.equip_price())
                self.player.win_equipment(self.data)

            elif isinstance(self.player.task, HeadingToMarketTask | SellTask):
                if isinstance(self.player.task, SellTask):
                    item = self.player.inventory[0]
                    amount = item.quantity * self.player.level
                    if " of " in item.name:
                        amount *= (1 + random.below_low(10)) * (
                            1 + random.below_low(self.player.level)
                        )
                    self.player.inventory.pop(0)
                    self.player.inventory.add_gold(amount)
                if len(self.player.inventory):
                    item = self.player.inventory[0]
                    self.player.set_task(
                        SellTask(
                            "Selling " + indefinite(item.name, item.quantity),
                            1000,
                        )
                    )
                    break

            elif isinstance(self.player.task, PlotTask):
                self.complete_act()

            old = self.player.task
            if self.player.queue:
                self.player.set_task(self.player.queue.pop(0))
            elif self.player.inventory.encum_bar.done:
                self.player.set_task(
                    HeadingToMarketTask("Heading to market to sell loot", 4000)
                )
            elif not isinstance(old, KillTask | HeadingToKillingFieldsTask):
                if self.player.inventory.gold > self.player.equip_price():
                    self.player.set_task(
                        BuyTask(
                            "Negotiating purchase of better equipment", 5000
                        )
                    )
                else:
                    self.player.set_task(
                        HeadingToKillingFieldsTask(
                            "Heading to the killing fields", 4000
                        )
                    )
            else:
                self.player.set_task(
                    monster_task(
                        self.data,
                        self.player.level,
                        self.player.quest_book.monster,
                    )
                )

    def complete_act(self) -> None:
        self.player.quest_book.increment_act()
        self.player.quest_book.plot_bar.reset(
            60 * 60 * (1 + 5 * self.player.quest_book.act)
        )
        if self.player.quest_book.act > 1:
            self.player.win_item(self.data)
            self.player.win_equipment(self.data)

    def complete_quest(self) -> None:
        self.player.quest_book.quest_bar.reset(50 + random.below(100))
        if self.player.quest_book.current_quest:
            logger.info(
                "Quest completed: %s", self.player.quest_book.current_quest
            )
            random.choice(
                [
                    functools.partial(self.player.win_spell, self.data),
                    functools.partial(self.player.win_equipment, self.data),
                    self.player.win_stat,
                    functools.partial(self.player.win_item, self.data),
                ]
            )()

        self.player.quest_book.monster = None
        caption = ""
        choice = random.below(5)
        if choice == 0:
            self.player.quest_book.monster = unnamed_monster(
                self.data, self.player.level, iterations=3
            )
            caption = "Exterminate " + definite(
                self.player.quest_book.monster.name, 2
            )
        elif choice == 1:
            caption = "Seek " + definite(interesting_item(self.data), 1)
        elif choice == 2:
            caption = "Deliver this " + boring_item(self.data)
        elif choice == 3:
            caption = "Fetch me " + indefinite(boring_item(self.data), 1)
        elif choice == 4:
            monster = unnamed_monster(
                self.data, self.player.level, iterations=1
            )
            caption = "Placate " + definite(monster.name, 2)
        else:
            raise AssertionError

        self.player.quest_book.add_quest(caption)
        self.player.quest_book.emit("start_quest", caption)

    def interplot_cinematic(self) -> None:
        def enqueue(task: BaseTask) -> None:
            self.player.queue.append(task)
            self.dequeue()

        choice = random.below(3)
        if choice == 0:
            enqueue(
                RegularTask(
                    "Exhausted, you arrive at a friendly oasis "
                    "in a hostile land",
                    1000,
                )
            )
            enqueue(
                RegularTask("You greet old friends and meet new allies", 2000)
            )
            enqueue(
                RegularTask(
                    "You are privy to a council of powerful do-gooders", 2000
                )
            )
            enqueue(
                RegularTask("There is much to be done. You are chosen!", 1000)
            )

        elif choice == 1:
            enqueue(
                RegularTask(
                    "Your quarry is in sight, "
                    "but a mighty enemy bars your path!",
                    1000,
                )
            )

            nemesis = named_monster(self.data, self.player.level + 3)

            enqueue(
                RegularTask(
                    f"A desperate struggle commences with {nemesis}", 4000
                )
            )

            s = random.below(3)
            for i in itertools.count(start=1):
                if i > random.below(1 + self.player.quest_book.act + 1):
                    break
                s += 1 + random.below(2)
                if s % 3 == 0:
                    enqueue(
                        RegularTask(
                            f"Locked in grim combat with {nemesis}", 2000
                        )
                    )
                elif s % 3 == 1:
                    enqueue(
                        RegularTask(
                            f"{nemesis} seems to have the upper hand", 2000
                        )
                    )
                elif s % 3 == 2:
                    enqueue(
                        RegularTask(
                            f"You seem to gain the advantage over {nemesis}",
                            2000,
                        )
                    )
                else:
                    raise AssertionError()

            enqueue(
                RegularTask(
                    f"Victory! {nemesis} is slain! "
                    "Exhausted, you lose consciousness",
                    3000,
                )
            )
            enqueue(
                RegularTask(
                    "You awake in a friendly place, but the road awaits", 2000
                )
            )

        elif choice == 2:
            nemesis = impressive_guy(self.data)
            enqueue(
                RegularTask(
                    "Oh sweet relief! "
                    f"You've reached the kind protection of {nemesis}",
                    2000,
                )
            )
            enqueue(
                RegularTask(
                    "There is rejoicing, "
                    f"and an unnerving encounter with {nemesis} in private",
                    3000,
                )
            )
            enqueue(
                RegularTask(
                    f"You forget your {boring_item(self.data)} "
                    "and go back to get it",
                    2000,
                )
            )
            enqueue(
                RegularTask(
                    "What's this!? You overhear something shocking!", 2000
                )
            )
            enqueue(
                RegularTask(f"Could {nemesis} be a dirty double-dealer?", 2000)
            )
            enqueue(
                RegularTask(
                    "Who can possibly be trusted with this news!? -- "
                    "Oh yes, of course",
                    3000,
                )
            )

        else:
            raise AssertionError

        enqueue(
            PlotTask(
                f"Loading {act_name(self.player.quest_book.act + 1)}", 1000
            )
        )


def special_item(data: GameData) -> str:
    return (
        interesting_item(data)
        + " of "
        + cast(str, random.choice(data.item_ofs))
    )


def interesting_item(data: GameData) -> str:
    return (
        cast(str, random.choice(data.item_attrib))
        + " "
        + cast(str, random.choice(data.specials))
    )


def boring_item(data: GameData) -> str:
    return cast(str, random.choice(data.boring_items))


def impressive_guy(data: GameData) -> str:
    if random.below(2):
        title = cast(str, random.choice(data.impressive_titles))
        race = cast(Race, random.choice(data.races))
        return f"the {title} of the {plural(race.name)}"
    title = cast(str, random.choice(data.impressive_titles))
    return f"{title} {generate_name()} of {generate_name()}"


def unnamed_monster(data: GameData, level: int, iterations: int) -> Monster:
    result = cast(Monster, random.choice(data.monsters))
    for _ in range(iterations):
        alternative = cast(Monster, random.choice(data.monsters))
        if abs(level - alternative.level) < abs(level - result.level):
            result = alternative
    return result


def named_monster(data: GameData, level: int) -> str:
    monster = unnamed_monster(data, level, iterations=4)
    return generate_name() + " the " + monster.name


def pick_equipment(
    source: Sequence[EquipmentPreset], goal: int
) -> EquipmentPreset:
    result = cast(EquipmentPreset, random.choice(source))
    for _ in range(5):
        alternative = cast(EquipmentPreset, random.choice(source))
        if abs(goal - alternative.quality) < abs(goal - result.quality):
            result = alternative
    return result


def monster_task(
    data: GameData, player_level: int, quest_monster: Monster | None
) -> KillTask:
    level = player_level
    for _ in range(level):
        if random.odds(2, 5):
            level += random.below(2) * 2 - 1
    if level < 1:
        level = 1

    is_definite = False
    monster: Monster | None = None
    if random.odds(1, 25):
        # use an NPC every once in a while
        race = random.choice(data.races)
        if random.odds(1, 2):
            result = (
                "passing " + race.name + " " + random.choice(data.classes).name
            )
        else:
            result = (
                random.choice_low(data.titles)
                + " "
                + generate_name()
                + " the "
                + race.name
            )
            is_definite = True
        lev = level
    elif quest_monster and random.odds(1, 4):
        # use the quest monster
        monster = quest_monster
        result = monster.name
        lev = monster.level
    else:
        # pick the monster out of so many random ones closest to the level
        # we want
        monster = unnamed_monster(data, level, iterations=5)
        result = monster.name
        lev = monster.level

    qty = 1
    if level - lev > 10:
        # lev is too low. multiply
        qty = (level + random.below(max(lev, 1))) // max(lev, 1)
        if qty < 1:
            qty = 1
        level //= qty

    if level - lev <= -10:
        result = "imaginary " + result
    elif level - lev < -5:
        i = 10 + level - lev
        i = 5 - random.below(i + 1)
        result = sick(i, young(lev - level - i, result))
    elif level - lev < 0 and random.below(2) == 1:
        result = sick(level - lev, result)
    elif level - lev < 0:
        result = young(level - lev, result)
    elif level - lev >= 10:
        result = "messianic " + result
    elif level - lev > 5:
        i = 10 - (level - lev)
        i = 5 - random.below(i + 1)
        result = big(i, special(level - lev - i, result))
    elif level - lev > 0 and random.below(2) == 1:
        result = big(level - lev, result)
    elif level - lev > 0:
        result = special(level - lev, result)

    lev = level
    level = lev * qty
    if not is_definite:
        result = indefinite(result, qty)

    duration = (2 * 3 * level * 1000) // player_level
    # with a single verb, skip the roll so the stock RNG stream is unchanged
    verb = (
        data.combat_verbs[0]
        if len(data.combat_verbs) == 1
        else cast(str, random.choice(data.combat_verbs))
    )
    description = verb.replace(TARGET_PLACEHOLDER, result)
    return KillTask(description, duration, monster=monster)


@dataclass
class _Roll:
    stats: Stats
    seed: RngState  # generator state before the roll
    after: RngState


class StatsBuilder:
    def __init__(self, rng: Alea | None = None) -> None:
        self._rng = rng or Alea()
        self.history: list[_Roll] = []

    @property
    def seed(self) -> RngState:
        """Generator state the current stats were rolled from.

        Like upstream, a new character's game continues from this state,
        so its first rolls replay the stat roll's numbers.
        """
        return self.history[-1].seed

    def roll(self) -> Stats:
        seed = self._rng.state()
        with random.using(self._rng):
            values: dict[StatType, int] = {
                stat: 3 + random.below(6) + random.below(6) + random.below(6)
                for stat in PRIME_STATS
            }
            values[StatType.hp_max] = (
                random.below(8) + values[StatType.condition] // 6
            )
            values[StatType.mp_max] = (
                random.below(8) + values[StatType.intelligence] // 6
            )
        stats = Stats(values)
        self.history.append(_Roll(stats, seed, self._rng.state()))
        return stats

    def unroll(self) -> Stats:
        if len(self.history) > 1:
            self.history.pop()
        self._rng = Alea.from_state(self.history[-1].after)
        return self.history[-1].stats


def create_player(
    name: str,
    race: Race,
    class_: Class,
    stats: Stats,
    seed: RngState | None = None,
) -> Player:
    player = Player(
        birthday=datetime.datetime.now(),
        name=name,
        race=race,
        class_=class_,
        stats=stats,
        rng=Alea.from_state(seed) if seed is not None else None,
    )
    return player
