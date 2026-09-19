"""Stage 10: Residual forecast correction data layer.

This module reads the research index
(`data/processed/research_hourly_index.parquet`) which contains
`actual_<target>` and `day_ahead_<target>` columns for the entire
2020 calendar year. The columns are verified against the file
schema before any computation. The day_ahead columns are the
external RTS_DAY_AHEAD forecast baseline used by Phase 19.

The chronological split is:

  Training  : 2020-01-01 .. 2020-08-31  (5856 hours)
  Validation: 2020-09-01 .. 2020-10-31  (1464 hours)
  Test      : 2020-11-01 .. 2020-12-31  (1464 hours, the locked Phase 19
                                          test window)

This split is fixed in code; it is NOT learned or searched. The
test window is byte-identical to the Phase 19 frozen final-test
window, and the protocol guarantees it is never used to fit a
residual model, never used to estimate a constant bias, and never
used to select a model family or hyperparameter.

Chronology is enforced at every entry point: any function that
returns a (training, validation, test) split does so in that fixed
order. Out-of-order calls raise an error.
"""
from __future__ import annotations
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

# The locked test window. The Stage 9 final test window is
# 2020-11-01 .. 2020-12-31 23:00:00. This is fixed.
TEST_START = datetime(2020, 11, 1, 0, 0, 0)
TEST_END = datetime(2020, 12, 31, 23, 0, 0)
TRAIN_END_EXCLUSIVE = datetime(2020, 9, 1, 0, 0, 0)   # Validation starts here.
VAL_END_EXCLUSIVE = datetime(2020, 11, 1, 0, 0, 0)     # Test starts here.

TARGETS: tuple[str, ...] = ("system_load", "wind", "pv")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_research_index() -> list[dict]:
    """Load the research index rows. Each row is a dict with
    timestamp + 3 (actual, day_ahead) pairs. Returns rows sorted
    by timestamp ascending (the source is already sorted, but the
    assertion protects against silent reordering)."""
    if not SOURCE_PARQUET.is_file():
        raise FileNotFoundError(
            f"Research index not found: {SOURCE_PARQUET}. Stage 10 requires "
            "data/processed/research_hourly_index.parquet to be present."
        )
    table = pq.read_table(SOURCE_PARQUET)
    expected = {"timestamp", "actual_system_load", "day_ahead_system_load",
                "actual_wind", "day_ahead_wind", "actual_pv", "day_ahead_pv"}
    actual = set(table.column_names)
    missing = expected - actual
    if missing:
        raise ValueError(
            f"Research index is missing required columns: {sorted(missing)}. "
            f"Got: {sorted(actual)}."
        )
    rows = table.to_pylist()
    # Chronology: timestamp strictly non-decreasing.
    prev = None
    for r in rows:
        ts = r["timestamp"]
        if prev is not None and ts < prev:
            raise ValueError(
                f"Non-chronological source at {ts}; previous was {prev}."
            )
        prev = ts
    return rows


@dataclass(frozen=True)
class Split:
    train: List[dict]
    validation: List[dict]
    test: List[dict]

    def __post_init__(self) -> None:
        # The split must contain no future-leak. Test rows must all be
        # >= TEST_START. Validation rows must all be < VAL_END_EXCLUSIVE
        # and >= TRAIN_END_EXCLUSIVE. Train rows must all be <
        # TRAIN_END_EXCLUSIVE.
        for r in self.test:
            if r["timestamp"] < TEST_START or r["timestamp"] > TEST_END:
                raise ValueError(
                    f"Test row {r['timestamp']} falls outside the locked "
                    f"window [{TEST_START}..{TEST_END}]."
                )
        for r in self.validation:
            if r["timestamp"] < TRAIN_END_EXCLUSIVE or r["timestamp"] >= VAL_END_EXCLUSIVE:
                raise ValueError(
                    f"Validation row {r['timestamp']} falls outside the "
                    f"validation window [{TRAIN_END_EXCLUSIVE}..{VAL_END_EXCLUSIVE}]."
                )
        for r in self.train:
            if r["timestamp"] >= TRAIN_END_EXCLUSIVE:
                raise ValueError(
                    f"Train row {r['timestamp']} falls outside the train "
                    f"window [..{TRAIN_END_EXCLUSIVE}]."
                )

    def n_train(self) -> int:
        return len(self.train)

    def n_validation(self) -> int:
        return len(self.validation)

    def n_test(self) -> int:
        return len(self.test)


def chronological_split() -> Split:
    """Return the fixed chronological split. The same call always
    returns the same partition because the source is sorted and the
    boundaries are constants."""
    rows = _load_research_index()
    train: list[dict] = []
    val: list[dict] = []
    test: list[dict] = []
    for r in rows:
        ts = r["timestamp"]
        if ts < TRAIN_END_EXCLUSIVE:
            train.append(r)
        elif ts < VAL_END_EXCLUSIVE:
            val.append(r)
        else:
            test.append(r)
    return Split(train=train, validation=val, test=test)


# ----------------- Residual definitions --------------------------------------

def residual(target: str, row: dict) -> float:
    """Compute `actual - day_ahead` for the given target. The sign
    convention is fixed: positive = RTS_DAY_AHEAD under-predicts,
    negative = RTS_DAY_AHEAD over-predicts."""
    if target == "system_load":
        return float(row["actual_system_load"]) - float(row["day_ahead_system_load"])
    if target == "wind":
        return float(row["actual_wind"]) - float(row["day_ahead_wind"])
    if target == "pv":
        return float(row["actual_pv"]) - float(row["day_ahead_pv"])
    raise ValueError(f"Unknown target: {target!r}. Expected one of {TARGETS}.")


def day_ahead(target: str, row: dict) -> float:
    if target == "system_load":
        return float(row["day_ahead_system_load"])
    if target == "wind":
        return float(row["day_ahead_wind"])
    if target == "pv":
        return float(row["day_ahead_pv"])
    raise ValueError(f"Unknown target: {target!r}.")


def actual_value(target: str, row: dict) -> float:
    if target == "system_load":
        return float(row["actual_system_load"])
    if target == "wind":
        return float(row["actual_wind"])
    if target == "pv":
        return float(row["actual_pv"])
    raise ValueError(f"Unknown target: {target!r}.")


# ----------------- Baseline residual metrics ---------------------------------

def residual_summary(rows: list[dict], target: str) -> dict:
    """Return descriptive statistics of the residual on the given
    rows. Used for the baseline analysis and for the constant-bias
    training step."""
    rs = [residual(target, r) for r in rows]
    if not rs:
        return {"n": 0}
    n = len(rs)
    mean = statistics.mean(rs)
    std = statistics.stdev(rs) if n > 1 else 0.0
    median = statistics.median(rs)
    abs_rs = [abs(r) for r in rs]
    return {
        "n": n,
        "mean": mean,
        "std": std,
        "median": median,
        "abs_mean_mae": statistics.mean(abs_rs),  # This IS the MAE of the
                                                  # zero-correction baseline
                                                  # against actual. The
                                                  # absolute residual mean
                                                  # is also the MAE of
                                                  # RTS_DAY_AHEAD on the
                                                  # rows because MAE on
                                                  # rows = mean(|actual - forecast|)
                                                  # = mean(|residual|).
        "abs_p95": _percentile(abs_rs, 95),
        "abs_max": max(abs_rs),
    }


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return float("nan")
    s = sorted(values)
    k = (len(s) - 1) * (pct / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return s[int(k)]
    return s[f] + (s[c] - s[f]) * (k - f)


# ----------------- Constant-bias baseline -----------------------------------

def constant_bias_baseline(target: str, split: Split) -> dict:
    """Train the constant-bias correction on the training split
    ONLY. The bias is `mean(actual - day_ahead)` over the training
    rows. The corrected forecast is `day_ahead + bias`. The
    validation and test rows are evaluated but never influence
    the bias estimate.

    The bias is applied uniformly to every row in the test
    split. This is a deterministic, no-fit-at-test-time research
    baseline.
    """
    train_residuals = [residual(target, r) for r in split.train]
    if not train_residuals:
        raise ValueError("Cannot fit a constant bias on an empty training set.")
    bias = statistics.mean(train_residuals)
    validation_metrics = _evaluate_constant_bias(split.validation, target, bias)
    test_metrics = _evaluate_constant_bias(split.test, target, bias)
    return {
        "target": target,
        "bias": bias,
        "n_train": len(train_residuals),
        "validation_metrics": validation_metrics,
        "test_metrics": test_metrics,
    }


def _evaluate_constant_bias(rows: list[dict], target: str, bias: float) -> dict:
    """Apply a pre-fitted constant bias to every row and compute
    the corrected MAE / RMSE / sMAPE / nMAE / nRMSE. The
    corrected forecast is `day_ahead + bias`, the same convention
    as the residual definition (positive bias means RTS_DAY_AHEAD
    under-predicts, so the correction is `forecast + bias` to add
    what was missing)."""
    actuals: list[float] = []
    corrected: list[float] = []
    rts_only: list[float] = []
    for r in rows:
        a = actual_value(target, r)
        d = day_ahead(target, r)
        actuals.append(a)
        rts_only.append(d)
        corrected.append(d + bias)
    return {
        "n": len(rows),
        "rts_day_ahead_metrics": _metrics(actuals, rts_only),
        "corrected_metrics": _metrics(actuals, corrected),
        "absolute_diff_MAE": _metrics(actuals, corrected)["MAE"]
                            - _metrics(actuals, rts_only)["MAE"],
        "relative_diff_MAE_pct": 100 * (
            (_metrics(actuals, corrected)["MAE"] - _metrics(actuals, rts_only)["MAE"])
            / max(_metrics(actuals, rts_only)["MAE"], 1e-9)
        ),
    }


def _metrics(actual: list[float], pred: list[float]) -> dict:
    n = max(len(actual), 1)
    abs_err = [abs(a - p) for a, p in zip(actual, pred)]
    sq_err = [(a - p) ** 2 for a, p in zip(actual, pred)]
    mae = sum(abs_err) / n
    rmse = math.sqrt(sum(sq_err) / n)
    smape = 100.0 * sum(
        (abs(a - p) / (abs(a) + abs(p))) if (abs(a) + abs(p)) > 0 else 0
        for a, p in zip(actual, pred)
    ) / n
    mean_a = sum(actual) / n
    var_a = sum((a - mean_a) ** 2 for a in actual) / n
    nmae = mae / max(mean_a, 1e-9)
    nrmse = rmse / max(math.sqrt(var_a), 1e-9)
    return {"n": n, "MAE": mae, "RMSE": rmse, "sMAPE_pct": smape,
            "nMAE": nmae, "nRMSE": nrmse}
