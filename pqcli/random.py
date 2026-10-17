import contextlib
import time
from collections.abc import Callable, Generator, Sequence
from typing import TypeVar

RngState = tuple[float, float, float, int]

T = TypeVar("T")

_2_POW_32 = 0x100000000
_2_POW_MINUS_32 = 2.3283064365386963e-10


def _to_uint32(value: float) -> float:
    # JS `value >>> 0` for the non-negative values Mash produces
    return float(int(value) % _2_POW_32)


def _mash() -> Callable[[str], float]:
    n = float(0xEFC8249D)

    def mash(data: str) -> float:
        nonlocal n
        # JS strings are UTF-16, and charCodeAt() returns code units
        units = data.encode("utf-16-le")
        for i in range(0, len(units), 2):
            n += units[i] | (units[i + 1] << 8)
            h = 0.02519603282416938 * n
            n = _to_uint32(h)
            h -= n
            h *= n
            n = _to_uint32(h)
            h -= n
            n += h * _2_POW_32
        return _to_uint32(n) * _2_POW_MINUS_32

    return mash


class Alea:
    """Johannes Baagøe's Alea PRNG (MIT), as used by Progress Quest web.

    Ported bit for bit so that games seeded alike play out alike. Saves
    pickle this class by import path, so it must stay in this module.
    """

    def __init__(self, *args: str) -> None:
        if not args:
            args = (str(int(time.time() * 1000)),)
        mash = _mash()
        self._s0 = mash(" ")
        self._s1 = mash(" ")
        self._s2 = mash(" ")
        self._c = 1
        for arg in args:
            self._s0 -= mash(arg)
            if self._s0 < 0:
                self._s0 += 1
            self._s1 -= mash(arg)
            if self._s1 < 0:
                self._s1 += 1
            self._s2 -= mash(arg)
            if self._s2 < 0:
                self._s2 += 1

    @classmethod
    def from_state(cls, state: RngState) -> "Alea":
        rng = cls.__new__(cls)
        rng._s0, rng._s1, rng._s2, rng._c = state
        return rng

    def state(self) -> RngState:
        return (self._s0, self._s1, self._s2, self._c)

    def random(self) -> float:
        t = 2091639 * self._s0 + self._c * _2_POW_MINUS_32
        self._s0 = self._s1
        self._s1 = self._s2
        self._c = int(t)
        self._s2 = t - self._c
        return self._s2

    def uint32(self) -> int:
        return int(self.random() * _2_POW_32)


_current = Alea()


def seed(source: str) -> None:
    global _current
    _current = Alea(source)


@contextlib.contextmanager
def using(rng: Alea) -> Generator[None, None, None]:
    """Draw from rng instead of the shared generator inside the block."""
    global _current
    previous = _current
    _current = rng
    try:
        yield
    finally:
        _current = previous


def choice(source: Sequence[T]) -> T:
    return source[below(len(source))]


def choice_low(source: Sequence[T]) -> T:
    return source[below_low(len(source))]


def below(num: int) -> int:
    return _current.uint32() % num


def below_low(num: int) -> int:
    return min(below(num), below(num))


def odds(chance: int, out_of: int) -> bool:
    return below(out_of) < chance
