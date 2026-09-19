"""Stage 9A: Baseline forecasting error analysis.

This module reads the frozen `artifacts/research_tables/final_predictions.csv`
(1464 hourly rows per target across LOAD / WIND / PV) and produces a
per-target error analysis. It is purely descriptive: it never trains,
mutates, or invents measurements. All numeric values are recomputed
from the source artefact.

The analysis covers:

  * Overall MAE, RMSE, sMAPE, nMAE, nRMSE (the same metrics already
    used by Phase 19).
  * Signed error (mean bias).
  * Absolute-error distribution (median, P95, max).
  * Error sliced by hour-of-day, day-of-week, and month.
  * Error sliced by actual-value tertile (low / mid / high).

All outputs are written under
`artifacts/v2/forecasting_research/baseline_analysis/<target>/` and
the Phase 19 frozen artefacts are never read for any purpose other
than as a CSV data source.
"""
from __future__ import annotations
import csv
import hashlib
import json
import math
import statistics
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Iterable, List

ROOT = Path(__file__).resolve().parents[3]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _parse_ts(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")


def _load_predictions(path: Path) -> list[dict]:
    """Read the frozen prediction CSV. The file is read-only and is
    never modified. Column names are pinned by the Phase 19 protocol."""
    if not path.is_file():
        raise FileNotFoundError(
            f"Source artefact not found: {path}. Stage 9A reads ONLY from "
            "artifacts/research_tables/final_predictions.csv."
        )
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        required = ("timestamp", "target", "model", "prediction", "actual", "absolute_error")
        if not all(c in (reader.fieldnames or []) for c in required):
            raise ValueError(
                f"Source artefact is missing required columns: {required}. "
                f"Got: {reader.fieldnames}."
            )
        out: list[dict] = []
        for row in reader:
            out.append({
                "timestamp": row["timestamp"],
                "target": row["target"],
                "model": row["model"],
                "prediction": float(row["prediction"]),
                "actual": float(row["actual"]),
                "absolute_error": float(row["absolute_error"]),
            })
    return out


# ---------------- Metrics (re-implemented locally; consistent with
# src/smartgrid_mlops/experimental_design/metrics.py) ----------------

def _mae(actual: list[float], pred: list[float]) -> float:
    return sum(abs(a - p) for a, p in zip(actual, pred)) / max(len(actual), 1)


def _rmse(actual: list[float], pred: list[float]) -> float:
    n = max(len(actual), 1)
    return math.sqrt(sum((a - p) ** 2 for a, p in zip(actual, pred)) / n)


def _smape(actual: list[float], pred: list[float]) -> float:
    """Symmetric mean absolute percentage error (the Phase 19 formula).
    Returns percentage (0-200), not fraction."""
    if not actual:
        return float("nan")
    total = 0.0
    for a, p in zip(actual, pred):
        denom = abs(a) + abs(p)
        if denom == 0:
            continue
        total += abs(a - p) / denom
    return 100.0 * total / len(actual)


def _nmae(actual: list[float], pred: list[float]) -> float:
    mean_abs = sum(abs(a) for a in actual) / max(len(actual), 1)
    if mean_abs == 0:
        return float("nan")
    return _mae(actual, pred) / mean_abs


def _nrmse(actual: list[float], pred: list[float]) -> float:
    mean = sum(actual) / max(len(actual), 1)
    var = sum((a - mean) ** 2 for a in actual) / max(len(actual), 1)
    if var == 0:
        return float("nan")
    return _rmse(actual, pred) / math.sqrt(var)


def _signed_error(actual: list[float], pred: list[float]) -> float:
    """Mean of (actual - prediction). Positive = model under-predicts."""
    if not actual:
        return float("nan")
    return sum(a - p for a, p in zip(actual, pred)) / len(actual)


# ---------------- Per-target, per-model analysis ----------------

def per_target_per_model_metrics(rows: list[dict]) -> dict:
    """Return a nested dict: {target: {model: {metric: value}}}."""
    grouped: dict[str, dict[str, list[tuple[float, float]]]] = defaultdict(lambda: defaultdict(list))
    for r in rows:
        grouped[r["target"]][r["model"]].append((r["actual"], r["prediction"]))
    out: dict[str, dict[str, dict[str, float]]] = {}
    for target, models in grouped.items():
        out[target] = {}
        for model, pairs in models.items():
            a = [p[0] for p in pairs]
            p = [p[1] for p in pairs]
            abs_err = [abs(ai - pi) for ai, pi in pairs]
            out[target][model] = {
                "n": len(pairs),
                "MAE": _mae(a, p),
                "RMSE": _rmse(a, p),
                "sMAPE_pct": _smape(a, p),
                "nMAE": _nmae(a, p),
                "nRMSE": _nrmse(a, p),
                "signed_error": _signed_error(a, p),
                "abs_err_median": statistics.median(abs_err) if abs_err else float("nan"),
                "abs_err_p95": _percentile(abs_err, 95),
                "abs_err_max": max(abs_err) if abs_err else float("nan"),
            }
    return out


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


def _abs_err_dist(values: list[float]) -> dict:
    if not values:
        return {"n": 0, "median": float("nan"), "p95": float("nan"), "max": float("nan"),
                "mean": float("nan")}
    return {
        "n": len(values),
        "mean": statistics.mean(values),
        "median": statistics.median(values),
        "p95": _percentile(values, 95),
        "max": max(values),
    }


def error_by_hour_of_day(rows: list[dict]) -> dict:
    """Slice absolute error by hour-of-day (0-23). Returns a list of
    per-hour statistics."""
    by_hour: dict[int, list[float]] = defaultdict(list)
    for r in rows:
        h = _parse_ts(r["timestamp"]).hour
        by_hour[h].append(r["absolute_error"])
    out = []
    for h in range(24):
        d = _abs_err_dist(by_hour.get(h, []))
        d["hour"] = h
        out.append(d)
    return out


def error_by_day_of_week(rows: list[dict]) -> dict:
    by_dow: dict[int, list[float]] = defaultdict(list)
    for r in rows:
        d = _parse_ts(r["timestamp"]).weekday()  # 0=Mon
        by_dow[d].append(r["absolute_error"])
    out = []
    for d in range(7):
        stats = _abs_err_dist(by_dow.get(d, []))
        stats["day_of_week"] = d
        out.append(stats)
    return out


def error_by_month(rows: list[dict]) -> dict:
    by_month: dict[str, list[float]] = defaultdict(list)
    for r in rows:
        m = _parse_ts(r["timestamp"]).strftime("%Y-%m")
        by_month[m].append(r["absolute_error"])
    return [{"month": m, **_abs_err_dist(errs)} for m, errs in sorted(by_month.items())]


def error_by_actual_tertile(rows: list[dict]) -> dict:
    """Slice error by actual-value tertile (low / mid / high). Returns
    a list of per-tertile statistics."""
    actuals = sorted(r["actual"] for r in rows)
    if len(actuals) < 3:
        return []
    p33 = actuals[len(actuals) // 3]
    p67 = actuals[2 * len(actuals) // 3]
    by_tertile: dict[str, list[float]] = {"low": [], "mid": [], "high": []}
    for r in rows:
        a = r["actual"]
        if a < p33:
            by_tertile["low"].append(r["absolute_error"])
        elif a < p67:
            by_tertile["mid"].append(r["absolute_error"])
        else:
            by_tertile["high"].append(r["absolute_error"])
    return [
        {"tertile": t, "lower_bound": lo, "upper_bound": hi, **_abs_err_dist(errs)}
        for t, lo, hi, errs in [
            ("low", float("-inf"), p33, by_tertile["low"]),
            ("mid", p33, p67, by_tertile["mid"]),
            ("high", p67, float("inf"), by_tertile["high"]),
        ]
    ]


# ---------------- Top-level: write per-target baseline_analysis artefacts ----------------

def run_baseline_analysis(source_csv: Path, out_root: Path) -> dict:
    """Read the frozen predictions, compute the per-target analysis, and
    write it under `out_root/<target>/`. Returns a top-level manifest."""
    if not source_csv.is_file():
        raise FileNotFoundError(f"Source CSV not found: {source_csv}")
    source_sha = _sha(source_csv)
    rows = _load_predictions(source_csv)
    if not rows:
        raise ValueError(f"Source CSV is empty: {source_csv}")

    overall = per_target_per_model_metrics(rows)
    manifest: dict = {
        "source_path": str(source_csv),
        "source_sha256": source_sha,
        "n_total_rows": len(rows),
        "targets": sorted(overall.keys()),
        "models_per_target": {t: sorted(overall[t].keys()) for t in overall},
        "per_target_per_model": overall,
    }
    # Per-target files: one JSON with metrics + slices.
    written: list[str] = []
    for target in sorted(overall.keys()):
        target_rows = [r for r in rows if r["target"] == target]
        target_dir = out_root / target
        target_dir.mkdir(parents=True, exist_ok=True)
        per_target = {
            "target": target,
            "source_path": str(source_csv),
            "source_sha256": source_sha,
            "n_rows": len(target_rows),
            "n_distinct_models": len({r["model"] for r in target_rows}),
            "per_model_metrics": overall[target],
            "error_by_hour_of_day": error_by_hour_of_day(target_rows),
            "error_by_day_of_week": error_by_day_of_week(target_rows),
            "error_by_month": error_by_month(target_rows),
            "error_by_actual_tertile": error_by_actual_tertile(target_rows),
        }
        # Persist per-target analysis.
        path = target_dir / "analysis.json"
        path.write_text(json.dumps(per_target, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")
        written.append(str(path.relative_to(out_root.parent.parent)))

    # Top-level manifest.
    manifest_path = out_root / "manifest.json"
    manifest["per_target_files"] = written
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                             encoding="utf-8")
    return manifest
