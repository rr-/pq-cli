import random
import typing as T


def seed(source: T.Any) -> None:
    random.seed(source)


def choice(source: T.Iterable[T.Any]) -> T.Any:
    return random.choice(source)


def below(num: int) -> int:
    return random.randint(0, num - 1)


def below_low(num: int) -> int:
    return min(below(num), below(num))


def odds(chance: int, out_of: int) -> bool:
    return below(out_of) < chance
