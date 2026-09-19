"""Stage 11: Residual distribution analysis.

Compares the residual distribution per (target, fold) and asks
whether the Stage 10 candidate's test-window advantage could
plausibly be a distribution-shift artifact.

For each target and each fold (F-Aug, F-Sep, F-Oct, F-Nov,
F-Dec), this module records:

  * mean residual
  * standard deviation
  * median residual
  * 5th / 95th percentiles
  * MAE (mean absolute residual, which is the zero-correction RTS
    MAE on the fold)

The function `cross_fold_distribution_summary` then writes a
side-by-side comparison that shows the residual distribution
shift across folds. A large shift in mean or std between
training and test is a candidate explanation for an artificially
strong test-time result.

The skewness calculation uses the standard third-moment formula
without scipy (no new dependency). Skewness is a single number;
small samples can have high variance in this statistic. We do
not over-claim causality from skewness alone.
"""
from __future__ import annotations
import json
import math
import statistics
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from smartgrid_mlops.research_v2.residual.data import (
    TARGETS, residual, day_ahead, actual_value,
)
from smartgrid_mlops.research_v2.residual.features import DEFAULT_LAGS

from .folds import Fold, chronological_folds


DIST_DIR = Path(__file__).resolve().parents[4] / "artifacts" / "v2" / "research_validation" / "distribution_analysis"


@dataclass(frozen=True)
class FoldDistribution:
    fold_id: str
    target: str
    n: int
    mean: float
    stdev: float
    median: float
    p05: float
    p95: float
    abs_mean_mae: float
    skewness: float


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


def _skewness(values: list[float]) -> float:
    if len(values) < 3:
        return float("nan")
    m = statistics.mean(values)
    s = statistics.stdev(values)
    if s == 0:
        return 0.0
    n = len(values)
    return (sum((v - m) ** 3 for v in values) / n) / (s ** 3)


def fold_distribution(fold: Fold, target: str) -> FoldDistribution:
    residuals = [residual(target, r) for r in fold.validation]
    n = len(residuals)
    if n == 0:
        return FoldDistribution(fold.fold_id, target, 0,
                                float("nan"), float("nan"), float("nan"),
                                float("nan"), float("nan"), float("nan"),
                                float("nan"))
    abs_res = [abs(r) for r in residuals]
    return FoldDistribution(
        fold_id=fold.fold_id, target=target, n=n,
        mean=statistics.mean(residuals),
        stdev=statistics.stdev(residuals) if n > 1 else 0.0,
        median=statistics.median(residuals),
        p05=_percentile(residuals, 5),
        p95=_percentile(residuals, 95),
        abs_mean_mae=statistics.mean(abs_res),
        skewness=_skewness(residuals),
    )


def run_distribution_analysis(out_dir: Path = DIST_DIR) -> dict:
    """Run the per-fold distribution analysis and write a summary
    that explicitly shows the mean / std / abs_mean_mae shift
    between training (F-Aug is the last training month) and the
    locked test (F-Nov + F-Dec)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    folds = chronological_folds()
    per_target: dict[str, list[dict]] = {t: [] for t in TARGETS}
    for fold in folds:
        for target in TARGETS:
            d = fold_distribution(fold, target)
            per_target[target].append({
                "fold_id": d.fold_id, "n": d.n,
                "mean": d.mean, "stdev": d.stdev,
                "median": d.median, "p05": d.p05, "p95": d.p95,
                "abs_mean_mae": d.abs_mean_mae, "skewness": d.skewness,
            })
    # Per-target side-by-side: list of (fold_id, mean, std, mae).
    side_by_side: dict[str, list[dict]] = {}
    for t in TARGETS:
        side_by_side[t] = per_target[t]
    summary = {
        "schema": "stage_11_distribution_analysis_v1",
        "note": (
            "Each entry reports the residual distribution on the "
            "VALIDATION rows of that fold. The training rows are not "
            "included here; the comparison is across FOLDS, not "
            "between training and test. To compare train vs test, "
            "compare F-Aug (in-sample, last training month) against "
            "F-Nov + F-Dec (the locked Phase 19 test window)."
        ),
        "folds": [f.fold_id for f in folds],
        "per_target": per_target,
        "side_by_side": side_by_side,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    out_path = out_dir / "distribution_analysis.json"
    out_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n",
                         encoding="utf-8")
    return summary
