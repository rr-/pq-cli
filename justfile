default: run

# Run the game; extra arguments go to pqcli
run *args:
    uv run pqcli {{args}}

# Run with the curses interface
curses *args:
    uv run pqcli --curses {{args}}

# Run with the basic interface
basic *args:
    uv run pqcli --basic {{args}}

# Run the test suite; extra arguments go to pytest
test *args:
    uv run pytest {{args}}

# Re-record the gameplay parity fixtures (only when gameplay should change)
record-traces:
    uv run python tests/game_trace.py
