"""The curses UI, run for real in a pseudo-terminal."""

import re
import sys
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from helpers import DATA, hero, read_names, save_path, write_pqw, write_roster

from pqcli import pqw
from pqcli.config import PRIME_STATS, EquipmentType
from pqcli.mechanic import Player
from pqcli.roster import Roster

if sys.platform != "win32":
    from pty_app import (
        BACKSPACE,
        CTRL_T,
        CTRL_W,
        DOWN,
        ENTER,
        ESC,
        F5,
        F6,
        F10,
        LEFT,
        PAGE_DOWN,
        PAGE_UP,
        RIGHT,
        TAB,
        UP,
        PtyApp,
    )

pytestmark = pytest.mark.skipif(
    sys.platform == "win32", reason="needs a POSIX pseudo-terminal"
)

ROSTER_MENU = "[Q] Quit"
PANES = [
    " Character Sheet ",
    " Spell Book ",
    " Equipment ",
    " Inventory ",
    " Plot Development ",
    " Quests ",
]
STATS_RE = re.compile(r"\b(STR|CON|DEX|INT|WIS|CHA): (\d+)")

Start = Callable[..., "PtyApp"]


@pytest.fixture
def config(tmp_path: Path) -> Path:
    return tmp_path / "config"


@pytest.fixture
def start(config: Path, tmp_path: Path) -> Iterator[Start]:
    """Start pqcli with XDG_CONFIG_HOME in tmp_path; stopped at teardown."""
    apps: list[PtyApp] = []

    def start(*args: str, **kwargs: int) -> PtyApp:
        app = PtyApp(config, *args, cwd=tmp_path, **kwargs)
        apps.append(app)
        return app

    yield start
    for app in apps:
        app.close()


def quit_app(app: "PtyApp") -> None:
    app.wait_for(ROSTER_MENU)
    app.send("q")
    assert app.wait_exit() == 0


def shown_stats(app: "PtyApp") -> dict[str, int]:
    return {
        name: int(value) for name, value in STATS_RE.findall(app.screen_text())
    }


def name_box(app: "PtyApp") -> str:
    """The text in the character name box."""
    y = app.row_of("Choose character name:") + 3
    return app.lines[y].strip().strip("│").strip()


def focused_panes(app: "PtyApp") -> list[str]:
    return [pane for pane in PANES if app.is_reverse(pane)]


TASK_PROGRESS_RE = re.compile(r"^ *\d+\.\d\d% *$")


def task_row(app: "PtyApp") -> int | None:
    """The row of the task progress bar, the last one in the game view."""
    for y, line in reversed(list(enumerate(app.lines))):
        if TASK_PROGRESS_RE.match(line):
            return y
    return None


# roster ---------------------------------------------------------------


def test_roster_menu(start: Start, config: Path) -> None:
    write_roster(config, hero("Ann"))
    app = start("--no-colors")
    text = app.wait_for(ROSTER_MENU)
    for entry in [
        "[C] Create new character",
        "[P] Play",
        "[D] Delete character",
        "[I] Import character (.pqw)",
        "[E] Export character (.pqw)",
    ]:
        assert entry in text
    assert "█▄▄▀ █▀▀ ▄▀▀▄" in text  # the logo

    assert app.is_reverse("[C] Create")
    app.send(DOWN)
    app.wait_until(lambda _: app.is_reverse("[P] Play"), what="[P] focus")
    assert not app.is_reverse("[C] Create")
    app.send("j" + TAB)
    app.wait_until(lambda _: app.is_reverse("[I] Import"), what="[I] focus")
    app.send(UP + "k")
    app.wait_until(lambda _: app.is_reverse("[P] Play"), what="[P] focus")

    # Enter picks the highlighted entry
    app.send(ENTER)
    app.wait_for("Choose character to play:")
    app.send("q")
    quit_app(app)
    assert read_names(config) == ["Ann"]


def test_roster_menu_wraps_with_tab(start: Start, config: Path) -> None:
    write_roster(config, hero("Ann"))
    app = start("--no-colors")
    app.wait_for(ROSTER_MENU)
    app.send(UP)  # already at the top: stays there
    app.send(TAB * 5)
    app.wait_until(lambda _: app.is_reverse("[Q] Quit"), what="[Q] focus")
    app.send(DOWN)  # already at the bottom: stays there
    app.send(TAB)
    app.wait_until(lambda _: app.is_reverse("[C] Create"), what="[C] focus")
    app.send(ESC)
    assert app.wait_exit() == 0


def test_ctrl_c_saves_and_exits(start: Start, config: Path) -> None:
    write_roster(config, hero("Ann"))
    app = start()
    app.wait_for(ROSTER_MENU)
    app.send("\x03")
    assert app.wait_exit() == 0
    assert read_names(config) == ["Ann"]
    assert (config / "pqcli" / "save.dat.old").exists()


# creating a character -------------------------------------------------


def test_create_character(start: Start, config: Path) -> None:
    write_roster(config, hero("Ann"))
    app = start("--no-colors")
    app.wait_for(ROSTER_MENU)

    app.send("c")
    app.wait_for("Choose character name:")
    assert name_box(app)  # starts with a random name
    app.send(CTRL_W + "Zedd")
    app.wait_until(lambda _: name_box(app) == "Zedd", what="Zedd")
    app.send(BACKSPACE)
    app.wait_until(lambda _: name_box(app) == "Zed", what="Zed")
    app.send(F5)
    app.wait_until(lambda _: name_box(app) != "Zed", what="a random name")
    app.send(CTRL_W + "Zed" + ENTER)

    text = app.wait_for("Choose character race:")
    for i, race in enumerate(DATA.races[:9], 1):
        assert f"[{i}] {race.name}" in text
    app.send("2")

    text = app.wait_for("Choose character class:")
    for i, class_ in enumerate(DATA.classes[:9], 1):
        assert f"[{i}] {class_.name}" in text
    app.send("3")

    app.wait_for("Roll character stats:")
    first = shown_stats(app)
    assert list(first) == ["STR", "CON", "DEX", "INT", "WIS", "CHA"]
    assert all(3 <= value <= 18 for value in first.values())
    assert app.is_reverse("[F5   ] Roll")

    # Keys are handled in order, so once the focus has moved the stats
    # are final: three rolls and four unrolls (one too many) give the
    # first roll back.
    app.send(F5 * 3 + F6 * 4 + DOWN)
    app.wait_until(lambda _: app.is_reverse("[F6   ] Unroll"), what="focus")
    assert shown_stats(app) == first

    app.send(F5 + UP)
    app.wait_until(lambda _: app.is_reverse("[F5   ] Roll"), what="focus")
    rolled = shown_stats(app)
    app.send(F10)

    text = app.wait_for(" Character Sheet ")
    assert re.search(r"Name +Zed\b", text)
    assert re.search(rf"Race +{DATA.races[1].name}", text)
    assert re.search(rf"Class +{DATA.classes[2].name}", text)
    assert re.search(rf"STR +{rolled['STR']}\b", text)

    # the new character is saved right away
    [_, zed] = load_players(config)
    assert zed.name == "Zed"
    assert zed.race == DATA.races[1]
    assert zed.class_ == DATA.classes[2]
    assert {stat.value: zed.stats[stat] for stat in PRIME_STATS} == rolled

    app.send("q")
    quit_app(app)


def load_players(config: Path) -> list[Player]:
    return Roster.load(save_path(config)).players


def test_name_view_buttons(start: Start, config: Path) -> None:
    write_roster(config, hero("Ann"))
    app = start("--no-colors", "--no-save")
    app.wait_for(ROSTER_MENU)
    app.send("c")
    app.wait_for("Choose character name:")
    app.send(CTRL_W + "Zed")
    app.wait_until(lambda _: name_box(app) == "Zed", what="Zed")

    # Down leaves the text box for the buttons below it
    app.send(DOWN)
    app.wait_until(
        lambda _: app.is_reverse("[F5   ] Generate"), what="F5 focus"
    )
    app.send(ENTER)
    app.wait_until(lambda _: name_box(app) != "Zed", what="a random name")

    app.send("j")
    app.wait_until(lambda _: app.is_reverse("[F10  ] Continue"), what="F10")
    app.send(DOWN + DOWN)  # stops at the last button
    app.wait_until(lambda _: app.is_reverse("[Esc  ] Cancel"), what="Esc")
    app.send(UP + "k" + "k")  # back in the text box; no further up
    app.wait_until(
        lambda _: not app.is_reverse("[F5   ] Generate"), what="text box"
    )
    # typing works again in the text box
    app.send(CTRL_W + "Bo" + TAB + TAB)
    app.wait_until(lambda _: app.is_reverse("[F10  ] Continue"), what="F10")
    assert name_box(app) == "Bo"
    app.send(ENTER)
    app.wait_for("Choose character race:")

    # cancelling the race goes back to the name, which is kept
    app.send("q")
    app.wait_for("Choose character name:")
    assert name_box(app) == "Bo"

    # Tab wraps around to the text box
    app.send(TAB * 4 + "b")
    app.wait_until(lambda _: name_box(app) == "Bob", what="Bob")
    app.send(F10)
    app.wait_for("Choose character race:")
    app.send(ESC)
    app.wait_for("Choose character name:")

    # the Cancel button goes back to the roster
    app.send(TAB * 3)
    app.wait_until(lambda _: app.is_reverse("[Esc  ] Cancel"), what="Esc")
    app.send(ENTER)
    app.wait_for(ROSTER_MENU)

    # so does q while a button has focus, and Esc in the text box
    app.send("c")
    app.wait_for("Choose character name:")
    app.send(TAB + "q")
    app.wait_for(ROSTER_MENU)
    app.send("c")
    app.wait_for("Choose character name:")
    app.send(ESC)
    app.wait_for(ROSTER_MENU)

    # a blank name cancels too
    app.send("c")
    app.wait_for("Choose character name:")
    app.send(CTRL_W + "   " + ENTER)
    app.wait_for(ROSTER_MENU)

    # with --no-save a new character is not written
    app.send("c")
    app.wait_for("Choose character name:")
    app.send(ENTER)
    app.wait_for("Choose character race:")
    app.send(ENTER)
    app.wait_for("Choose character class:")
    app.send(ENTER)
    app.wait_for("Roll character stats:")
    app.send(F10)
    app.wait_for(" Character Sheet ")
    app.send("q")
    quit_app(app)
    assert read_names(config) == ["Ann"]


def test_create_character_back_and_forth(start: Start, config: Path) -> None:
    write_roster(config, hero("Ann"))
    app = start("--no-colors")
    app.wait_for(ROSTER_MENU)
    app.send("c")
    app.wait_for("Choose character name:")
    app.send(CTRL_W + "Cy" + ENTER)

    race = DATA.races[2]
    class_ = DATA.classes[1]
    app.wait_for("Choose character race:")
    app.send("3")
    app.wait_for("Choose character class:")
    app.send("q")
    # back at the race, with the chosen one highlighted
    app.wait_for("Choose character race:")
    assert app.is_reverse(f"[3] {race.name}")
    app.send(DOWN + UP + ENTER)
    app.wait_for("Choose character class:")
    app.send("2")
    app.wait_for("Roll character stats:")
    app.send(ESC)
    app.wait_for("Choose character class:")
    assert app.is_reverse(f"[2] {class_.name}")
    app.send(ENTER)

    # the buttons in the stats view
    app.wait_for("Roll character stats:")
    app.send(TAB + TAB)
    app.wait_until(lambda _: app.is_reverse("[F10  ] Continue"), what="F10")
    app.send(TAB + TAB)  # wraps around
    app.wait_until(lambda _: app.is_reverse("[F5   ] Roll"), what="F5")
    first = shown_stats(app)
    app.send(ENTER + "j" + ENTER + "k")
    app.wait_until(lambda _: app.is_reverse("[F5   ] Roll"), what="F5")
    assert shown_stats(app) == first  # rolled, then unrolled
    app.send(UP + DOWN * 4)  # clamped at both ends
    app.wait_until(lambda _: app.is_reverse("[Esc  ] Cancel"), what="Esc")
    app.send(ENTER)
    app.wait_for("Choose character class:")
    app.send(ENTER)
    app.wait_for("Roll character stats:")
    app.send(TAB + TAB)
    app.wait_until(lambda _: app.is_reverse("[F10  ] Continue"), what="F10")
    app.send(ENTER)

    text = app.wait_for(" Character Sheet ")
    assert re.search(r"Name +Cy\b", text)
    assert re.search(rf"Race +{race.name}", text)
    assert re.search(rf"Class +{class_.name}", text)
    app.send("q")
    quit_app(app)
    assert read_names(config) == ["Ann", "Cy"]


# playing --------------------------------------------------------------


def test_game_view(start: Start, config: Path) -> None:
    player = hero("Ann", ticks=20000)
    write_roster(config, hero("Bob"), player)
    app = start("--no-colors")
    app.wait_for(ROSTER_MENU)
    app.send("p")

    text = app.wait_for("Choose character to play:")
    assert "[1] Bob the " in text
    assert f"[2] Ann the {player.race.name} (Act I)" in text
    assert f"Level {player.level} {player.class_.name}" in text
    app.send("2")

    rows = len(app.lines)
    text = app.wait_until(
        lambda s: (
            all(pane in s for pane in PANES) and task_row(app) == rows - 1
        ),
        what="the game view",
    )
    assert re.search(r"Name +Ann\b", text)
    assert re.search(rf"Level +{player.level}\b", text)
    assert "Experience (" in text
    assert "Encumbrance (" in text
    assert "[X] Prologue" in text
    assert "[ ] Act I" in text
    assert re.search(rf"Gold +{player.inventory.gold}", text)
    for spell in player.spell_book:
        assert spell.name in text
    for quest in player.quest_book.quests[-3:]:
        assert quest[:20] in text
    weapon = player.equipment[EquipmentType.weapon]
    assert weapon
    assert re.search(rf"Weapon +{weapon}", text)
    # the task and its progress run along the bottom
    assert app.lines[-2].rstrip().endswith("...")

    app.send("q")
    quit_app(app)


def test_game_view_focus(start: Start, config: Path) -> None:
    write_roster(config, hero("Ann"))
    app = start("--no-colors", "--load-save", "1")
    app.wait_until(lambda s: all(p in s for p in PANES), what="panes")

    def expect(pane: str) -> None:
        app.wait_until(
            lambda _: focused_panes(app) == [pane], what=f"{pane} focus"
        )

    expect(" Character Sheet ")
    for pane in PANES[1:] + PANES[:1]:
        app.send(TAB)
        expect(pane)

    # The panes form a 3x2 grid: sheet, equipment and plot on top. This
    # route takes every move between neighbours once.
    moves = [
        (UP + "l", " Equipment "),  # nothing above the sheet
        (RIGHT, " Plot Development "),
        (DOWN, " Quests "),
        (LEFT, " Inventory "),
        ("h", " Spell Book "),
        (UP, " Character Sheet "),
        (DOWN, " Spell Book "),
        (DOWN + RIGHT, " Inventory "),  # nothing below the spell book
        (UP, " Equipment "),
        ("j", " Inventory "),
        (RIGHT, " Quests "),
        ("k", " Plot Development "),
        (RIGHT + LEFT, " Equipment "),  # nothing right of the plot
        (LEFT, " Character Sheet "),
    ]
    for key, pane in moves:
        app.send(key)
        expect(pane)

    # keys that mean nothing here are ignored
    app.send("x")
    app.send("t")  # a cheat, but cheats are off
    app.send(TAB)
    expect(" Spell Book ")

    app.send(ESC)
    quit_app(app)


def test_game_view_scrolls_by_page(start: Start, config: Path) -> None:
    player = hero("Ann", ticks=20000)
    quests = player.quest_book.quests
    assert len(quests) > 10
    write_roster(config, player)
    # small enough that the quests do not fit their pane
    app = start("--no-colors", "--load-save", "1", rows=24)
    app.wait_until(lambda s: all(p in s for p in PANES), what="panes")
    first, last = quests[0][:20], quests[-1][:20]
    text = app.wait_for(last)
    assert first not in text

    # PgUp/PgDn only scroll the focused pane
    app.send(PAGE_UP)
    app.send(TAB * 5)
    app.wait_until(
        lambda _: focused_panes(app) == [" Quests "], what="quests focus"
    )
    assert last in app.screen_text()

    app.send(PAGE_UP * len(quests))
    app.wait_for(first)
    assert last not in app.screen_text()

    app.send(PAGE_DOWN * len(quests))
    app.wait_for(last)
    assert first not in app.screen_text()

    # the other panes take the keys too, or ignore them
    for _ in range(5):
        app.send(TAB)
        app.send(PAGE_DOWN + PAGE_UP)
    app.wait_until(
        lambda _: focused_panes(app) == [" Plot Development "],
        what="plot focus",
    )

    app.send("q")
    quit_app(app)


def test_load_save_starts_in_the_game(start: Start, config: Path) -> None:
    write_roster(config, hero("Ann"), hero("Bob"))
    app = start("--load-save", "2")
    text = app.wait_for(" Character Sheet ")
    assert re.search(r"Name +Bob\b", text)
    # leaving the game shows the roster rather than quitting
    app.send("q")
    quit_app(app)
    assert read_names(config) == ["Ann", "Bob"]


def test_many_characters(start: Start, config: Path) -> None:
    players = [hero(f"Hero{i}") for i in range(1, 12)]
    write_roster(config, *players)
    app = start("--no-colors")
    app.wait_for(ROSTER_MENU)
    app.send("p")
    text = app.wait_for("Choose character to play:")
    assert "[1] Hero1 the " in text
    assert "[0] Hero10 the " in text
    assert "[-] Hero11 the " in text
    # the eleventh has no key, but can be picked with the cursor
    app.send(DOWN * 10)
    app.wait_until(lambda _: app.is_reverse("[-] Hero11"), what="Hero11")
    app.send(ENTER)
    text = app.wait_for(" Character Sheet ")
    assert re.search(r"Name +Hero11\b", text)
    app.send("q")
    quit_app(app)


def test_cheats(start: Start, config: Path) -> None:
    write_roster(config, hero("Ann"))
    app = start("--cheats", "--no-save", "--load-save", "1")
    app.wait_until(lambda s: all(p in s for p in PANES), what="panes")

    def level() -> int:
        found = re.search(r"Level +(\d+)", app.screen_text())
        assert found
        return int(found.group(1))

    def xp_to_go() -> int:
        found = re.search(r"Experience \((\d+) XP to go\)", app.screen_text())
        assert found
        return int(found.group(1))

    assert level() == 1
    start_xp = xp_to_go()
    # t is one tick, T a hundred: 100 seconds of game time in all,
    # far more than passes on its own before the wait times out
    app.send("t" + "T" * 10)
    app.wait_until(lambda _: xp_to_go() < start_xp, what="experience")
    assert level() == 1

    # ^T is 10000 ticks at once, about 17 minutes of game time; three
    # of them reach level 2 with time to spare
    app.send(CTRL_T * 3)
    app.wait_until(lambda _: level() > 1, what="a level up")

    app.send("q")
    quit_app(app)


# resizing -------------------------------------------------------------


def menu_x(app: "PtyApp") -> int:
    return app.lines[app.row_of("[P] Play")].index("[P] Play")


def test_resize(start: Start, config: Path) -> None:
    write_roster(config, hero("Ann", ticks=3000))
    app = start()
    app.wait_for(ROSTER_MENU)
    wide_x = menu_x(app)

    app.resize(30, 80)
    app.wait_until(
        lambda s: "[P] Play" in s and menu_x(app) < wide_x,
        what="the menu to move",
    )

    app.send("p")
    app.wait_for("Choose character to play:")
    app.send("1")
    app.wait_until(lambda _: task_row(app) == 29, what="the game view")
    assert all(pane in app.screen_text() for pane in PANES)

    app.resize(40, 120)
    app.wait_until(lambda _: task_row(app) == 39, what="the task to move")
    text = app.screen_text()
    assert all(pane in text for pane in PANES)

    # far too small to fit: still runs and recovers
    app.resize(8, 30)
    app.send(TAB)
    app.resize(40, 120)
    app.wait_until(lambda _: task_row(app) == 39, what="the task to move")
    app.send("q")
    app.wait_for(ROSTER_MENU)

    app.resize(12, 40)
    app.resize(40, 120)
    quit_app(app)


# deleting -------------------------------------------------------------


def test_delete_character(start: Start, config: Path) -> None:
    write_roster(config, hero("Ann"), hero("Bob"))
    app = start()
    app.wait_for(ROSTER_MENU)

    # with colors, the highlight is a background color, not reverse
    y = app.row_of("[C] Create")
    x = app.lines[y].index("[C] Create")
    focused = app.screen.buffer[y][x]
    assert not focused.reverse
    assert focused.bg != app.screen.buffer[y + 1][x].bg

    app.send("d")
    app.wait_for("Choose character to delete:")
    app.send("1")
    text = app.wait_for("[Y] Yes")
    assert "Ann" in text
    assert "[N] No" in text

    # no goes back to the list
    app.send("n")
    app.wait_for("Choose character to delete:")
    app.send("1")
    app.wait_for("[Y] Yes")
    app.send("y")
    app.wait_for(ROSTER_MENU)

    app.send("d")
    text = app.wait_for("Choose character to delete:")
    assert "Ann the" not in text
    assert "[1] Bob the" in text
    app.send(ESC)
    quit_app(app)
    assert read_names(config) == ["Bob"]


# importing and exporting ----------------------------------------------


def input_box(app: "PtyApp") -> str:
    """The text in the text input box."""
    y = app.row_of("[Enter] Continue") - 2
    return app.lines[y].strip().strip("│").strip()


def test_import(start: Start, config: Path, tmp_path: Path) -> None:
    write_roster(config, hero("Ann"))
    source = write_pqw(tmp_path / "cid.pqw", hero("Cid"), online=True)
    app = start()
    app.wait_for(ROSTER_MENU)
    app.send("i")
    app.wait_for("Import from .pqw file:")
    assert input_box(app) == ""
    app.send("cid.pqwx" + BACKSPACE)
    app.wait_until(lambda _: input_box(app) == "cid.pqw", what="the path")
    app.send(ENTER)

    text = app.wait_for("Imported Cid.")
    assert "dropped 'online': pqcli plays offline only" in text
    app.send(ENTER)
    app.wait_for(ROSTER_MENU)
    assert read_names(config) == ["Ann", "Cid"]
    quit_app(app)
    assert source.exists()


def test_import_without_saving(
    start: Start, config: Path, tmp_path: Path
) -> None:
    write_roster(config, hero("Ann"))
    source = write_pqw(tmp_path / "cid.pqw", hero("Cid"))
    app = start("--no-save")
    app.wait_for(ROSTER_MENU)
    app.send("i")
    app.wait_for("Import from .pqw file:")
    app.send(str(source) + ENTER)
    app.wait_for("Imported Cid.")
    app.send("q")
    app.wait_for(ROSTER_MENU)
    app.send("p")
    text = app.wait_for("Choose character to play:")
    assert "[2] Cid the" in text
    app.send("q")
    quit_app(app)
    assert read_names(config) == ["Ann"]


def test_import_failures(start: Start, config: Path, tmp_path: Path) -> None:
    write_roster(config, hero("Ann"))
    (tmp_path / "bad.pqw").write_text("garbage!")
    app = start()
    app.wait_for(ROSTER_MENU)

    app.send("i")
    app.wait_for("Import from .pqw file:")
    app.send("bad.pqw" + ENTER)
    app.wait_for("Cannot import: not a .pqw file")
    app.send(ESC)
    app.wait_for(ROSTER_MENU)

    # a long path keeps its end in view
    long_name = "x" * 100 + "/missing.pqw"
    app.send("i")
    app.wait_for("Import from .pqw file:")
    app.send(long_name)
    app.wait_until(
        lambda _: input_box(app).endswith("/missing.pqw"), what="the path"
    )
    assert len(input_box(app)) < len(long_name)
    app.send(ENTER)
    text = app.wait_for("Cannot import: cannot read")
    assert "[Enter] OK" in text
    app.send("q")
    app.wait_for(ROSTER_MENU)

    # Esc and an empty path both cancel
    app.send("i")
    app.wait_for("Import from .pqw file:")
    app.send(ESC)
    app.wait_for(ROSTER_MENU)
    app.send("i")
    app.wait_for("Import from .pqw file:")
    app.send("abc" + CTRL_W + "  " + ENTER)
    app.wait_for(ROSTER_MENU)

    quit_app(app)
    assert read_names(config) == ["Ann"]


def test_export(start: Start, config: Path, tmp_path: Path) -> None:
    write_roster(config, hero("Ann"), hero("Bob"))
    app = start()
    app.wait_for(ROSTER_MENU)
    app.send("e")
    app.wait_for("Choose character to export:")
    app.send("2")
    app.wait_for("Export Bob to .pqw file:")
    assert input_box(app) == "Bob.pqw"

    # Esc goes back to the character list
    app.send(ESC)
    app.wait_for("Choose character to export:")
    app.send("2")
    app.wait_for("Export Bob to .pqw file:")
    app.send(ENTER)
    app.wait_for("Exported Bob to Bob.pqw.")
    assert pqw.read_file(tmp_path / "Bob.pqw", DATA)[0].name == "Bob"
    app.send(ENTER)
    app.wait_for(ROSTER_MENU)

    # the same file again is refused
    app.send("e")
    app.wait_for("Choose character to export:")
    app.send("1")
    app.wait_for("Export Ann to .pqw file:")
    app.send(CTRL_W + "Bob.pqw" + ENTER)
    app.wait_for("Cannot export: Bob.pqw already exists")
    app.send(ENTER)
    app.wait_for(ROSTER_MENU)

    app.send("e")
    app.wait_for("Choose character to export:")
    app.send("1")
    app.wait_for("Export Ann to .pqw file:")
    app.send(CTRL_W + str(tmp_path / "sub" / "ann.pqw") + ENTER)
    app.wait_for("Cannot export: cannot write")
    app.send(ENTER)
    app.wait_for(ROSTER_MENU)

    app.send("e")
    text = app.wait_for("Choose character to export:")
    assert "[Q] Cancel" in text
    app.send(ESC)

    quit_app(app)
    assert pqw.read_file(tmp_path / "Bob.pqw", DATA)[0].name == "Bob"
    assert not (tmp_path / "sub").exists()
