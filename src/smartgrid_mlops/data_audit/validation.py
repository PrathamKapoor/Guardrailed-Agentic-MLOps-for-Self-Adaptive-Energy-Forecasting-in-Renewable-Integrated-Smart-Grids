"""Audit validation constants and source checksum checks."""

from __future__ import annotations

import hashlib
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def source_checksums(root: Path, relative_paths: list[str]) -> dict[str, str]:
    return {relative: sha256(root / relative) for relative in relative_paths}
