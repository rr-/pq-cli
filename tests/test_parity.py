import pytest
from game_trace import FIXTURES, SEEDS, run_trace


@pytest.mark.parametrize("seed", SEEDS)
def test_gameplay_matches_recorded_trace(seed: str) -> None:
    # The fixtures pin down gameplay, RNG stream included. When a change is
    # meant to alter gameplay, re-record them with `just record-traces`.
    expected = (FIXTURES / f"parity_{seed}.txt").read_text().splitlines()
    assert run_trace(seed) == expected
