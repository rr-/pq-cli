from pathlib import Path

import pytest
from game_trace import run_trace

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.mark.parametrize("seed", ["alpha", "beta", "gamma"])
def test_gameplay_matches_recorded_trace(seed: str) -> None:
    # The fixtures were recorded before the word lists moved to data files;
    # stock data must reproduce them exactly, RNG stream included.
    expected = (FIXTURES / f"parity_{seed}.txt").read_text().splitlines()
    assert run_trace(seed) == expected
