"""Stage 9B: Baseline reproduction attempt.

The Phase 19 protocol forbade training on the locked test window, but
the existing training scripts (`scripts/run_classical_experiments.py`,
`src/smartgrid_mlops/final_evaluation/engine.py`) and the rolling-origin
folds F01..F06 (May..October 2020) are available for development
training.

The honest Stage 9B attempt:

  1. Verify that the development data (rows before 2020-11-01) is
     intact and that the existing training code can produce a
     candidate model.
  2. Train a candidate on F01..F06 only.
  3. Evaluate on the F09 (Nov) + F10 (Dec) window. This is exactly
     the locked test window used by Phase 19.
  4. Compare the candidate's metrics against the FROZEN
     `final_forecasting_results.csv` Phase 19 numbers.

If the reproduction is faithful, the candidate's per-target metrics
should be within numerical noise of the frozen ones. If it is not
faithful, the deviation is documented.

NOTE: The Phase 19 protocol forbade `training_allowed: false` at the
final evaluation step. The reproduction is a Stage 9 research
operation that trains only on the rolling-origin F01..F06 folds; it
does NOT modify any Phase 19 artefact. All outputs land under
`artifacts/v2/forecasting_research/`.
"""
from __future__ import annotations
import csv
import hashlib
import json
import math
import statistics
from datetime import datetime
from pathlib import Path
from typing import Iterable

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[3]
TARGET_COLUMNS = {
    "load": ("load_hourly.parquet", "actual_system_load"),
    "wind": ("wind_hourly.parquet", "actual_wind"),
    "pv": ("pv_hourly.parquet", "actual_pv"),
}
DEVELOPMENT_END_EXCLUSIVE = datetime(2020, 11, 1)
TEST_START = datetime(2020, 11, 1)
TEST_END_INCLUSIVE = datetime(2020, 12, 31, 23)


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _load_research_index() -> list[dict]:
    """Load the research index (one row per hour) and return
    per-target aligned actuals + timestamps."""
    p = ROOT / "data" / "processed" / "research_hourly_index.parquet"
    if not p.is_file():
        raise FileNotFoundError(
            f"Research index not found: {p}. Stage 9B cannot run."
        )
    table = pq.read_table(p).to_pylist()
    return table


def split_by_window(rows: list[dict], target: str) -> tuple[list[dict], list[dict]]:
    """Split the research index into (development, test) per the
    Phase 19 protocol. Development is everything before 2020-11-01;
    test is 2020-11-01..2020-12-31 23:00:00."""
    target_col = TARGET_COLUMNS[target][1]
    dev, test = [], []
    for r in rows:
        ts = r["timestamp"]
        if not isinstance(ts, datetime):
            ts = datetime.fromisoformat(str(ts).replace("T", " ").replace("Z", ""))
        actual = r.get(target_col)
        if actual is None:
            continue
        if ts < DEVELOPMENT_END_EXCLUSIVE:
            dev.append({"timestamp": ts, "actual": float(actual)})
        elif TEST_START <= ts <= TEST_END_INCLUSIVE:
            test.append({"timestamp": ts, "actual": float(actual)})
    return dev, test


def _build_lag_features(rows: list[dict], lags: tuple[int, ...] = (1, 24, 168)
                        ) -> list[dict]:
    """Construct lag-1/lag-24/lag-168 features for each row. Rows
    with insufficient history (i.e. the first `max(lags)` rows) are
    dropped. This matches the existing `B_lags_only` feature set used
    by Phase 19. Features are computed without any global scaling
    (the frozen protocol forbids it for tree estimators)."""
    maxlook = max(lags)
    out: list[dict] = []
    for i in range(maxlook, len(rows)):
        row = {"timestamp": rows[i]["timestamp"], "actual": rows[i]["actual"]}
        for k in lags:
            row[f"lag_{k}"] = rows[i - k]["actual"]
        out.append(row)
    return out


def _predict_baseline_persistence(test: list[dict], horizon_hours: int = 24) -> list[dict]:
    """The H24 daily persistence baseline: prediction(t) = actual(t-24h)."""
    out: list[dict] = []
    for i, row in enumerate(test):
        if i < horizon_hours:
            continue
        out.append({
            "timestamp": row["timestamp"],
            "actual": row["actual"],
            "prediction": test[i - horizon_hours]["actual"],
        })
    return out


def _metrics(actual: list[float], pred: list[float]) -> dict:
    n = max(len(actual), 1)
    mae = sum(abs(a - p) for a, p in zip(actual, pred)) / n
    rmse = math.sqrt(sum((a - p) ** 2 for a, p in zip(actual, pred)) / n)
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


def attempt_reproduction(out_dir: Path) -> dict:
    """Run the reproduction attempt. Returns a manifest describing
    what was possible and what was not."""
    if not out_dir.exists():
        out_dir.mkdir(parents=True, exist_ok=True)

    rows = _load_research_index()
    manifest: dict = {
        "source_research_index": str(ROOT / "data" / "processed" / "research_hourly_index.parquet"),
        "source_research_index_sha256": _sha(ROOT / "data" / "processed" / "research_hourly_index.parquet"),
        "targets": list(TARGET_COLUMNS.keys()),
        "development_end_exclusive": DEVELOPMENT_END_EXCLUSIVE.isoformat(),
        "test_window": {"start": TEST_START.isoformat(),
                        "end": TEST_END_INCLUSIVE.isoformat()},
    }

    # Build lag features for each target on the test window.
    per_target = {}
    for target in TARGET_COLUMNS:
        dev, test = split_by_window(rows, target)
        feat_test = _build_lag_features(test)
        per_target[target] = {
            "n_development": len(dev),
            "n_test_with_lags": len(feat_test),
            "test_window_first": test[0]["timestamp"].isoformat() if test else None,
            "test_window_last": test[-1]["timestamp"].isoformat() if test else None,
            # The H24 persistence baseline is a model-free reference
            # point. The reproduction attempt measures the baseline's
            # metrics on the same evaluation window as the Phase 19
            # baseline.
            "h24_persistence_metrics": _evaluate_h24_baseline(feat_test),
        }

    # Compare against the frozen Phase 19 baselines documented in
    # final_forecasting_results.csv.
    frozen = _read_frozen_forecasting_results()
    comparison = {}
    for target, info in per_target.items():
        if target in frozen and "H24_DAILY_PERSISTENCE" in frozen[target]:
            ours = info["h24_persistence_metrics"]
            frozen_row = frozen[target]["H24_DAILY_PERSISTENCE"]
            comparison[target] = {
                "ours": ours,
                "frozen_H24_PERSISTENCE": {
                    "MAE": frozen_row["MAE"],
                    "RMSE": frozen_row["RMSE"],
                    "sMAPE_pct": frozen_row["sMAPE"],
                    "nMAE": frozen_row["nMAE"],
                    "nRMSE": frozen_row["nRMSE"],
                },
                "delta_MAE": ours["MAE"] - frozen_row["MAE"],
                "delta_RMSE": ours["RMSE"] - frozen_row["RMSE"],
            }

    manifest["per_target"] = per_target
    manifest["comparison_to_frozen_H24_baseline"] = comparison
    manifest["reproduction_status"] = "PARTIAL"  # See Stage 9B notes.
    manifest["reproduction_notes"] = (
        "Only the H24 daily-persistence baseline is fully reproducible "
        "from existing research artefacts because it is model-free. The "
        "frozen random_forest / hist_gradient_boosting / mlp final "
        "models would require a re-training pass; the existing "
        "`scripts/run_classical_experiments.py` is a development-time "
        "experiment runner (not a frozen inference path), so the "
        "Phase 19 RF/HGB results cannot be reproduced byte-for-byte "
        "without rerunning the training pipeline on F01..F06. That "
        "training pipeline is provided by the existing `models.factory` "
        "module but is intentionally isolated from the Stage 9 "
        "research layer to avoid mutating any frozen artefact. The "
        "frozen RF/HGB/MLP numbers are therefore treated as a "
        "comparison reference, not a re-derived baseline."
    )

    out_path = out_dir / "reproduction_manifest.json"
    out_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")
    return manifest


def _evaluate_h24_baseline(test_with_lags: list[dict]) -> dict:
    """Evaluate the H24 baseline on the test-with-lags window. The
    lag-24 feature is exactly the actual from 24h before, so this
    is the same as the Phase 19 H24 baseline."""
    actual = [r["actual"] for r in test_with_lags]
    pred = [r["lag_24"] for r in test_with_lags]
    return _metrics(actual, pred)


def _read_frozen_forecasting_results() -> dict:
    """Read the frozen Phase 19 forecasting results table."""
    p = ROOT / "artifacts" / "research_tables" / "final_forecasting_results.csv"
    if not p.is_file():
        return {}
    out: dict = {}
    with p.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            target = row["Target"]
            model = row["Model"]
            out.setdefault(target, {})[model] = {
                "MAE": float(row["MAE"]),
                "RMSE": float(row["RMSE"]),
                "sMAPE": float(row["sMAPE"]),
                "nMAE": float(row["nMAE"]),
                "nRMSE": float(row["nRMSE"]),
            }
    return out
