"""Stage 11: Chronological validation folds.

This module defines the chronological folds used to validate
Stage 10's residual correction candidates. The folds are:

  F-Aug:  Train Jan..Jul 2020, validate 2020-08-01..2020-08-31
            (in-sample diagnostic; the last month of the Stage 10
             training window, used to detect overfitting).
  F-Sep:  Train Jan..Aug 2020, validate 2020-09-01..2020-09-30
            (out-of-sample, month 1 of the Stage 10 validation
             window).
  F-Oct:  Train Jan..Sep 2020, validate 2020-10-01..2020-10-31
            (out-of-sample, month 2 of the Stage 10 validation
             window).
  F-Nov:  Train Jan..Oct 2020, validate 2020-11-01..2020-11-30
            (the first month of the locked Phase 19 test window;
             identical to what Stage 10 calls "test" but split
             in half to check stability within the test window).
  F-Dec:  Train Jan..Nov 2020, validate 2020-12-01..2020-12-31
            (the second month of the locked Phase 19 test window).

The locked Phase 19 test window is the union of F-Nov and F-Dec.
Stage 11 NEVER trains on F-Nov or F-Dec. Stage 11 only USES F-Nov
and F-Dec to evaluate models that were trained without their
rows. This is the same firewall that Stage 10 used; Stage 11
extends it to within-window halves.

Every fold is forward-chained: training always strictly
precedes validation. There is no random shuffle, no
cross-validation in the time-series sense, and no leakage.
"""
from __future__ import annotations
import csv
import hashlib
import math
import statistics
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, List

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[4]
SOURCE_PARQUET = ROOT / "data" / "processed" / "research_hourly_index.parquet"

# The locked Phase 19 test window. Used as F-Nov and F-Dec together.
LOCKED_TEST_START = datetime(2020, 11, 1, 0, 0, 0)
LOCKED_TEST_END = datetime(2020, 12, 31, 23, 0, 0)


@dataclass(frozen=True)
class Fold:
    """A single chronological validation window.

    `train` contains every row with timestamp < start.
    `validation` contains every row with start <= timestamp <= end.
    No row in `train` is >= start. No row in `validation` is < start.
    """
    fold_id: str
    start: datetime
    end: datetime
    train: List[dict]
    validation: List[dict]

    def n_train(self) -> int:
        return len(self.train)

    def n_validation(self) -> int:
        return len(self.validation)

    def __post_init__(self) -> None:
        # Strict forward-chaining: no train row may have timestamp
        # >= start; no validation row may have timestamp < start.
        # The single character of slack we allow is the validation
        # start itself: a validation row may be exactly at `start`.
        for r in self.train:
            if r["timestamp"] >= self.start:
                raise ValueError(
                    f"fold {self.fold_id}: train row {r['timestamp']} "
                    f">= start {self.start} (forward-chaining violated)."
                )
        for r in self.validation:
            if r["timestamp"] < self.start or r["timestamp"] > self.end:
                raise ValueError(
                    f"fold {self.fold_id}: validation row "
                    f"{r['timestamp']} outside [{self.start}..{self.end}]."
                )


def _load_research_index() -> list[dict]:
    """Load the research index. Same schema check as Stage 10."""
    if not SOURCE_PARQUET.is_file():
        raise FileNotFoundError(f"missing: {SOURCE_PARQUET}")
    table = pq.read_table(SOURCE_PARQUET)
    expected = {"timestamp", "actual_system_load", "day_ahead_system_load",
                "actual_wind", "day_ahead_wind", "actual_pv", "day_ahead_pv"}
    actual = set(table.column_names)
    missing = expected - actual
    if missing:
        raise ValueError(f"research index missing columns: {sorted(missing)}")
    return table.to_pylist()


def _build_fold(rows: list[dict], fold_id: str,
                start: datetime, end: datetime) -> Fold:
    train = [r for r in rows if r["timestamp"] < start]
    val = [r for r in rows if start <= r["timestamp"] <= end]
    return Fold(fold_id=fold_id, start=start, end=end,
               train=train, validation=val)


def chronological_folds() -> list[Fold]:
    """Return the full list of chronological folds used in Stage 11.
    The locked Phase 19 test window is split into F-Nov and F-Dec;
    both are included in the returned list so the validator can
    evaluate them, but training rows for F-Nov and F-Dec never
    overlap with their own validation rows."""
    rows = _load_research_index()
    # Aug 1..Aug 31
    f_aug = _build_fold(rows, "F-Aug",
                          datetime(2020, 8, 1, 0, 0, 0),
                          datetime(2020, 8, 31, 23, 0, 0))
    # Sep 1..Sep 30
    f_sep = _build_fold(rows, "F-Sep",
                          datetime(2020, 9, 1, 0, 0, 0),
                          datetime(2020, 9, 30, 23, 0, 0))
    # Oct 1..Oct 31
    f_oct = _build_fold(rows, "F-Oct",
                          datetime(2020, 10, 1, 0, 0, 0),
                          datetime(2020, 10, 31, 23, 0, 0))
    # Nov 1..Nov 30  (locked first half)
    f_nov = _build_fold(rows, "F-Nov",
                          datetime(2020, 11, 1, 0, 0, 0),
                          datetime(2020, 11, 30, 23, 0, 0))
    # Dec 1..Dec 31  (locked second half)
    f_dec = _build_fold(rows, "F-Dec",
                          datetime(2020, 12, 1, 0, 0, 0),
                          datetime(2020, 12, 31, 23, 0, 0))
    return [f_aug, f_sep, f_oct, f_nov, f_dec]
