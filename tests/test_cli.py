import os
import subprocess
import sys
from pathlib import Path

from test_pqw import played

from pqcli.game_data import load_game_data
from pqcli.pqw import read_file, write_file


def pqcli(
    config: Path, *args: str, cwd: Path | None = None
) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "XDG_CONFIG_HOME": str(config)}
    return subprocess.run(
        [sys.executable, "-m", "pqcli", *args],
        capture_output=True,
        text=True,
        env=env,
        cwd=cwd,
    )


def test_import_then_export(tmp_path: Path) -> None:
    data = load_game_data()
    source = tmp_path / "in.pqw"
    write_file(played(3000).player, source, data)

    result = pqcli(tmp_path, "--import-save", str(source))
    assert result.returncode == 0, result.stderr
    assert result.stdout == "Imported Exportée\n"
    assert (tmp_path / "pqcli" / "save.dat").exists()

    listed = pqcli(tmp_path, "--list-saves")
    assert listed.stdout == "1. Exportée\n"

    target = tmp_path / "out.pqw"
    result = pqcli(tmp_path, "--export-save", "1", str(target))
    assert result.returncode == 0, result.stderr
    assert read_file(target, data)[0].name == "Exportée"


def test_import_bad_file_changes_nothing(tmp_path: Path) -> None:
    bad = tmp_path / "bad.pqw"
    bad.write_text("garbage!")
    result = pqcli(tmp_path, "--import-save", str(bad))
    assert result.returncode == 1
    assert "not a .pqw file" in result.stderr
    assert not (tmp_path / "pqcli" / "save.dat").exists()


def test_export_rejects_unknown_character(tmp_path: Path) -> None:
    result = pqcli(tmp_path, "--export-save", "3", str(tmp_path / "x.pqw"))
    assert result.returncode == 1
    assert "Invalid player" in result.stderr
    assert not (tmp_path / "x.pqw").exists()
