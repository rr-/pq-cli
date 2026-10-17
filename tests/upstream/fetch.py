"""Fetch Progress Quest web's game logic for the upstream comparison tests.

The files are downloaded from the public site into a cache directory, never
into this repository. Their hashes are pinned, so a change on the site fails
loudly instead of silently changing what the tests compare against.
"""

import hashlib
import os
import sys
import urllib.request
from pathlib import Path

BASE_URL = "https://progressquest.com/play/"

# Matches pq-web 3e9431b (2024-03-18) apart from http -> https URL edits.
FILES = {
    "config.js": (
        "cc76f256057d6ddbf7010f1b94e59913b935b9980138ed5e800bdd1e5ff5ec4e"
    ),
    "main.js": (
        "63926cda54b232c5e5be4e97123710ee4ab2dbd1faa213b21ddc01dab54a1ce0"
    ),
    "newguy.js": (
        "ac99e6524b1e8602f571515fc24f5c177e11d17ae4c6233dc43ff3aad079c7a5"
    ),
}


def cache_dir() -> Path:
    if "PQ_WEB_DIR" in os.environ:
        return Path(os.environ["PQ_WEB_DIR"])
    base = os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache"
    return Path(base) / "pqcli" / "pq-web"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def is_fetched(directory: Path) -> bool:
    return all(
        (directory / name).is_file()
        and _sha256((directory / name).read_bytes()) == digest
        for name, digest in FILES.items()
    )


def fetch(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for name, digest in FILES.items():
        path = directory / name
        if path.is_file() and _sha256(path.read_bytes()) == digest:
            continue
        url = BASE_URL + name
        with urllib.request.urlopen(url, timeout=30) as response:
            data = response.read()
        actual = _sha256(data)
        if actual != digest:
            raise SystemExit(
                f"{url} changed upstream: expected sha256 {digest}, "
                f"got {actual}. Review the change, then update FILES in "
                f"{__file__}."
            )
        path.write_bytes(data)


if __name__ == "__main__":
    target = cache_dir()
    try:
        fetch(target)
    except OSError as ex:
        print(f"cannot fetch upstream into {target}: {ex}", file=sys.stderr)
        sys.exit(1)
    print(target)
