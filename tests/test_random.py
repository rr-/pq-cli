import pickle

import pytest

from pqcli import random
from pqcli.random import Alea

# First outputs and resulting state of upstream's JS Alea(seed).uint32()
VECTORS = {
    "alpha": (
        [3768637044, 756790225, 3147161637, 1726577786, 279486812],
        (0.732755669625476, 0.4020002172328532, 0.06507309433072805, 368555),
    ),
    "": (
        [715789690, 2091287642, 486307, 3866591158, 760028033],
        (
            0.00011322717182338238,
            0.9002609080635011,
            0.17695781611837447,
            1018452,
        ),
    ),
    "1697543210123": (
        [3110287155, 2843160345, 1794106530, 2361562046, 1804721005],
        (
            0.41772297816351056,
            0.5498440111987293,
            0.42019435320980847,
            1384612,
        ),
    ),
    # Mash hashes UTF-16 code units, so the dragon counts as two
    "Ünïcødé 🐉": (
        [4162081648, 198215584, 541466577, 6418444, 2254846220],
        (
            0.12607001163996756,
            0.0014944104477763176,
            0.5249972967430949,
            96530,
        ),
    ),
}


@pytest.mark.parametrize("seed", VECTORS)
def test_alea_matches_upstream(seed: str) -> None:
    first, state = VECTORS[seed]
    rng = Alea(seed)
    assert [rng.uint32() for _ in first] == first
    assert rng.state() == state


def test_alea_state_round_trip() -> None:
    rng = Alea("alpha")
    rng.uint32()
    copy = Alea.from_state(rng.state())
    assert [copy.uint32() for _ in range(100)] == [
        rng.uint32() for _ in range(100)
    ]


def test_alea_pickles_with_its_state() -> None:
    rng = Alea("alpha")
    rng.uint32()
    copy = pickle.loads(pickle.dumps(rng))
    assert copy.state() == rng.state()


def test_unseeded_alea_differs() -> None:
    assert Alea().state() != Alea("alpha").state()


def test_below_is_uint32_modulo() -> None:
    # Random(n) = seed.uint32() % n
    random.seed("alpha")
    assert [random.below(1000) for _ in range(5)] == [
        n % 1000 for n in VECTORS["alpha"][0]
    ]


def test_using_restores_previous_generator() -> None:
    random.seed("outer")
    expected = Alea("outer").uint32() % 1000
    inner = Alea("inner")
    with random.using(inner):
        random.below(10)
    assert inner.state() != Alea("inner").state()
    assert random.below(1000) == expected
