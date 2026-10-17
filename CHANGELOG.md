# Changelog

## [Unreleased](https://github.com/rr-/pq-cli/compare/1.0.4...main) - ××××-××-××

**Gameplay**
- Changed the game mechanics to match the current web version of Progress Quest, which pqcli now plays exactly like, random rolls included (#21):
  - Changed the time needed to level up to grow exponentially: levels come much faster early on and much slower past level 49
  - Changed quests to be much shorter
  - Changed stat gains that favor the best stat to only consider the six prime stats
  - Changed item rewards on inventories past 250 kinds of items to sometimes add one more of something already carried
  - Changed impressive characters in cinematics to be named in the new styles, such as "the Queen of the Half Halflings"
  - Changed the cinematic texts to match the web version
  - Changed acts to begin as their loading task starts
  - Added the Chancellor, Baroness and Inquistor titles
- Changed the random number generator to the one the web version uses, stored with each character; existing characters get a new one on first load
- Changed roman numerals past 4000 to use the web version's T and A numerals
- Fixed the plot bar staying empty during the Prologue
- Fixed the quest log keeping 101 quests instead of 100
- Fixed "an" not being used before words starting with Ü

**Customization**
- Added data files for all word lists (monsters, spells, equipment, races, classes, titles and more), which can be replaced in `$XDG_CONFIG_HOME/pqcli/data/` or a directory given with `--data-dir` (#3)
- Added customizable combat descriptions (`combat_verbs.json`), which say "Executing" by default (#3)
- Added `--dump-data DIR` to copy the built-in word lists out for editing (#3)

**Saves**
- Added importing and exporting characters as `.pqw` files, the format of the web version, from both interfaces and with `--import-save` and `--export-save` (#21)

**Installation**
- Added a `Dockerfile` and `docker-compose.yml` to run the game in a container, with saves kept in a persistent volume
- Added character creation on first run when there are no saved characters yet

**Development**
- Added tests, including gameplay traces and a comparison with the web version's own code (`just test`)
- Added a `justfile`
- Changed the hooks to prek, with ruff in place of black and isort, ty for type checking, and a 50/72 commit message check
- Removed `poetry.lock`
