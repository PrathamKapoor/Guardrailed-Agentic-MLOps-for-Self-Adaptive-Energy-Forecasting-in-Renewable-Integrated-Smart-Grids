"""Loader for the replay source artefact.

The replay engine reads ONLY from
`artifacts/research_tables/final_predictions.csv`. This file is part of
the frozen Phase 19 evidence and must not be modified. The loader is
explicitly read-only and validates the schema before returning.

Schema contract (frozen):
    timestamp,target,model,prediction,actual,absolute_error

For each (timestamp, target) pair, the artefact carries rows for the
reference model and (where present) the strongest external benchmark
(RTS_DAY_AHEAD for LOAD/WIND; H24_DAILY_PERSISTENCE for PV). The replay
engine does not collapse them; every row is a distinct event.
"""
from __future__ import annotations
import csv
import hashlib
from dataclasses import dataclass
from pathlib import Path

from .schemas import SUPPORTED_TARGETS, Target

# Frozen source artefact. Resolved relative to the project root; the
# engine accepts an explicit override only for testing.
DEFAULT_SOURCE_REL = "artifacts/research_tables/final_predictions.csv"

REQUIRED_COLUMNS: tuple[str, ...] = (
    "timestamp", "target", "model", "prediction", "actual", "absolute_error",
)


@dataclass(frozen=True)
class ReplayRow:
    """One row of the source artefact, with numeric values cast to float.

    `timestamp` is kept as a string (the artefact's `YYYY-MM-DD HH:MM:SS`
    format) so the replay engine can preserve the source format. Numeric
    columns are cast; malformed numbers fail loud."""
    timestamp: str
    target: str
    model: str
    prediction: float
    actual: float
    absolute_error: float


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_columns(header: list[str]) -> None:
    missing = [c for c in REQUIRED_COLUMNS if c not in header]
    if missing:
        raise ValueError(
            f"Replay source is missing required columns: {missing}. "
            f"Got: {header}. Expected: {list(REQUIRED_COLUMNS)}."
        )


def load_rows(source_path: Path) -> list[ReplayRow]:
    """Load the source artefact as a list of typed rows.

    Raises:
        FileNotFoundError: if the source does not exist.
        ValueError: on missing columns, malformed numbers, or
            unsupported target. The engine never substitutes a
            placeholder; it fails explicitly.
    """
    if not source_path.is_file():
        raise FileNotFoundError(
            f"Replay source artefact not found: {source_path}. "
            "Stage 7 reads ONLY from artifacts/research_tables/final_predictions.csv. "
            "Re-run the project bootstrap or set QSMLOPS_PROJECT_ROOT to a checkout "
            "that contains the frozen Phase 19 evidence."
        )
    with source_path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        validate_columns(reader.fieldnames or [])
        out: list[ReplayRow] = []
        for line_no, row in enumerate(reader, start=2):  # line 1 is the header
            try:
                r = ReplayRow(
                    timestamp=row["timestamp"].strip(),
                    target=row["target"].strip(),
                    model=row["model"].strip(),
                    prediction=float(row["prediction"]),
                    actual=float(row["actual"]),
                    absolute_error=float(row["absolute_error"]),
                )
            except (KeyError, ValueError) as e:
                raise ValueError(
                    f"Malformed row at line {line_no} of {source_path}: {row!r} ({e})"
                ) from e
            if not r.timestamp:
                raise ValueError(f"Empty timestamp at line {line_no} of {source_path}")
            if r.target not in SUPPORTED_TARGETS:
                raise ValueError(
                    f"Unsupported target {r.target!r} at line {line_no} of "
                    f"{source_path}. Expected one of {SUPPORTED_TARGETS}."
                )
            out.append(r)
    if not out:
        raise ValueError(
            f"Replay source {source_path} contains no data rows. "
            "Empty dataset is not a valid input for replay."
        )
    return out


def filter_target(rows: list[ReplayRow], target: Target | None) -> list[ReplayRow]:
    if target is None:
        return list(rows)
    return [r for r in rows if r.target == target]
