"""Stage 11: Feature ablation.

The Stage 10 residual candidates use a 10-feature matrix
(6 calendar + day_ahead + 3 lagged residuals). This module
isolates which features actually drive the result by training
the same Ridge architecture on 7 different feature subsets:

  A. rts_only                 : [day_ahead]
  B. rts_plus_constant_bias   : [day_ahead] + constant-bias baseline
                                (constant bias is fitted on the
                                training rows; the model itself
                                has no trainable parameters.)
  C. rts_plus_lag              : [day_ahead, lag_1, lag_24, lag_168]
  D. rts_plus_calendar        : [day_ahead, hour, dow, doy]
  E. lag_only                 : [lag_1, lag_24, lag_168]
  F. calendar_only            : [hour, dow, doy]
  G. full                     : all 10 features (Stage 10 default)

Every configuration uses the same Ridge hyperparameters
(alpha=1.0, StandardScaler, fit_intercept=True) and the same
training window per fold. We measure MAE on the validation rows
of the fold. The MAE is then compared against the constant-bias
baseline (configuration B) and against the Stage 10 full model
(configuration G).

The honest goal is to determine WHICH features drive the result
and to report whether a simpler subset is sufficient. If the
result relies primarily on the day_ahead + constant-bias
combination, the Stage 10 HGB LOAD MAE=1.54 is actually a
deterministic-baseline result dressed up as a model.
"""
from __future__ import annotations
import json
import math
import statistics
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Tuple

from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

from smartgrid_mlops.research_v2.residual.data import (
    Split, TARGETS, residual, day_ahead, actual_value, _metrics,
)
from smartgrid_mlops.research_v2.residual.features import (
    _calendar_features, _build_features, DEFAULT_LAGS,
)

from .folds import Fold, chronological_folds
from .runner import _fold_to_split


ABLATION_DIR = Path(__file__).resolve().parents[4] / "artifacts" / "v2" / "research_validation" / "ablation_results"


@dataclass(frozen=True)
class AblationSpec:
    ablation_id: str
    description: str
    use_calendar: bool
    use_day_ahead: bool
    use_lags: bool
    include_constant_bias: bool  # for the deterministic baseline case


ABLATION_SPECS: list[AblationSpec] = [
    AblationSpec("A_rts_only",
                  "[day_ahead] only — pure baseline. Tests whether any "
                  "model at all is needed.",
                  use_calendar=False, use_day_ahead=True, use_lags=False,
                  include_constant_bias=False),
    AblationSpec("B_rts_plus_constant_bias",
                  "[day_ahead] + constant bias (no trainable parameters). "
                  "This is the deterministic Stage 10B baseline.",
                  use_calendar=False, use_day_ahead=True, use_lags=False,
                  include_constant_bias=True),
    AblationSpec("C_rts_plus_lag",
                  "[day_ahead, lag_1, lag_24, lag_168] — does lag structure "
                  "alone add value?",
                  use_calendar=False, use_day_ahead=True, use_lags=True,
                  include_constant_bias=False),
    AblationSpec("D_rts_plus_calendar",
                  "[day_ahead, hour, dow, doy] — does calendar alone add "
                  "value?",
                  use_calendar=True, use_day_ahead=True, use_lags=False,
                  include_constant_bias=False),
    AblationSpec("E_lag_only",
                  "[lag_1, lag_24, lag_168] only — pure lag model with no "
                  "day_ahead value.",
                  use_calendar=False, use_day_ahead=False, use_lags=True,
                  include_constant_bias=False),
    AblationSpec("F_calendar_only",
                  "[hour, dow, doy] only — pure calendar model with no "
                  "day_ahead value.",
                  use_calendar=True, use_day_ahead=False, use_lags=False,
                  include_constant_bias=False),
    AblationSpec("G_full",
                  "All 10 features (Stage 10 default).",
                  use_calendar=True, use_day_ahead=True, use_lags=True,
                  include_constant_bias=False),
]


def _select_lags(spec: AblationSpec) -> list[int]:
    if spec.use_lags:
        return list(DEFAULT_LAGS)
    return []


def _evaluate_ridge_with_subset(target: str, fold: Fold,
                                 spec: AblationSpec) -> dict:
    """Train a Ridge on the requested feature subset. Reuses
    Stage 10's `_build_features` (which already enforces the
    chronological lag firewall) and applies the subset mask
    AFTER building the full feature matrix. This guarantees
    that the lag-availability checks are unchanged from
    Stage 10; the only thing that varies across ablations is
    which columns of the matrix are presented to the model.

    The constant-bias ablation (spec B) is treated specially:
    we DO NOT fit a Ridge on day_ahead + bias (the Ridge would
    learn a scale-on-day-ahead correction, double-counting the
    bias). Instead, we just apply the constant bias directly.
    """
    split = _fold_to_split(fold)
    history = sorted(split.train + split.validation,
                    key=lambda r: r["timestamp"])
    lags = _select_lags(spec)
    X_full, y, d = _build_features(target, split.train, lags, history)
    if not X_full:
        return {"ablation_id": spec.ablation_id, "n_train": 0,
                "candidate_MAE": float("nan"),
                "baseline_MAE": float("nan")}

    # Constant bias is ALWAYS computed on the training residuals,
    # regardless of which feature subset is used. This is the
    # deterministic Stage 10B baseline.
    bias = statistics.mean(y) if y else 0.0

    # Spec A: pure RTS_DAY_AHEAD baseline. NO model at all.
    if spec.ablation_id == "A_rts_only":
        Xv, _, dv = _build_features(target, split.validation, lags, history)
        if not Xv:
            return {"ablation_id": spec.ablation_id, "n_train": 0,
                    "n_validation": 0, "candidate_MAE": float("nan"),
                    "baseline_MAE": float("nan")}
        actuals = [actual_value(target, r) for r in split.validation[:len(Xv)]]
        rts = [day_ahead(target, r) for r in split.validation[:len(Xv)]]
        cand_metrics = _metrics(actuals, rts)
        base_metrics = cand_metrics  # baseline == candidate
        return {
            "ablation_id": spec.ablation_id,
            "description": "RTS_DAY_AHEAD with NO correction. This is the "
                           "primary baseline. n_train=0 (no model fit).",
            "n_train": 0, "n_validation": len(Xv),
            "constant_bias": 0.0,
            "candidate_MAE": cand_metrics["MAE"],
            "candidate_RMSE": cand_metrics["RMSE"],
            "candidate_sMAPE_pct": cand_metrics["sMAPE_pct"],
            "baseline_MAE": base_metrics["MAE"],
            "baseline_RMSE": base_metrics["RMSE"],
            "relative_diff_MAE_pct": 0.0,
        }

    # If the spec is B (RTS + constant bias), apply the bias
    # directly without fitting a Ridge.
    if spec.ablation_id == "B_rts_plus_constant_bias":
        Xv, _, dv = _build_features(target, split.validation, lags, history)
        if not Xv:
            return {"ablation_id": spec.ablation_id, "n_train": len(X_full),
                    "n_validation": 0, "candidate_MAE": float("nan"),
                    "baseline_MAE": float("nan")}
        actuals = [actual_value(target, r) for r in split.validation[:len(Xv)]]
        rts = [day_ahead(target, r) for r in split.validation[:len(Xv)]]
        corrected = [d_i + bias for d_i in rts]
        cand_metrics = _metrics(actuals, corrected)
        base_metrics = _metrics(actuals, rts)
        return {
            "ablation_id": spec.ablation_id,
            "description": spec.description + " (post-hoc bias application, no Ridge).",
            "n_train": len(X_full),
            "n_validation": len(Xv),
            "constant_bias": bias,
            "candidate_MAE": cand_metrics["MAE"],
            "candidate_RMSE": cand_metrics["RMSE"],
            "candidate_sMAPE_pct": cand_metrics["sMAPE_pct"],
            "baseline_MAE": base_metrics["MAE"],
            "baseline_RMSE": base_metrics["RMSE"],
            "relative_diff_MAE_pct": 100 * (cand_metrics["MAE"] - base_metrics["MAE"]) / max(base_metrics["MAE"], 1e-9),
        }

    # Standard case: fit a Ridge on the requested column subset.
    keep_cols: list[int] = []
    if spec.use_calendar:
        keep_cols += [0, 1, 2, 3, 4, 5]
    if spec.use_day_ahead:
        keep_cols.append(6)
    if spec.use_lags:
        keep_cols += [7, 8, 9]
    if not keep_cols:
        # Pure constant-bias case: no features at all. Apply the
        # bias directly. This is identical to B but with zero
        # features; we keep it as a separate ablation for clarity.
        Xv, _, dv = _build_features(target, split.validation, lags, history)
        if not Xv:
            return {"ablation_id": spec.ablation_id, "n_train": len(X_full),
                    "n_validation": 0, "candidate_MAE": float("nan"),
                    "baseline_MAE": float("nan")}
        actuals = [actual_value(target, r) for r in split.validation[:len(Xv)]]
        rts = [day_ahead(target, r) for r in split.validation[:len(Xv)]]
        corrected = [d_i + bias for d_i in rts]
        cand_metrics = _metrics(actuals, corrected)
        base_metrics = _metrics(actuals, rts)
        return {
            "ablation_id": spec.ablation_id,
            "description": spec.description,
            "n_train": len(X_full), "n_validation": len(Xv),
            "constant_bias": bias,
            "candidate_MAE": cand_metrics["MAE"],
            "candidate_RMSE": cand_metrics["RMSE"],
            "candidate_sMAPE_pct": cand_metrics["sMAPE_pct"],
            "baseline_MAE": base_metrics["MAE"],
            "baseline_RMSE": base_metrics["RMSE"],
            "relative_diff_MAE_pct": 100 * (cand_metrics["MAE"] - base_metrics["MAE"]) / max(base_metrics["MAE"], 1e-9),
        }

    X = [[row[c] for c in keep_cols] for row in X_full]
    pipe = Pipeline([("scaler", StandardScaler()),
                     ("ridge", Ridge(alpha=1.0, fit_intercept=True))])
    pipe.fit(X, y)

    Xv, _, dv = _build_features(target, split.validation, lags, history)
    if not Xv:
        return {"ablation_id": spec.ablation_id, "n_train": len(X),
                "n_validation": 0,
                "candidate_MAE": float("nan"),
                "baseline_MAE": float("nan")}
    Xv_sub = [[row[c] for c in keep_cols] for row in Xv]
    predicted_residual = pipe.predict(Xv_sub)
    actuals = [actual_value(target, r) for r in split.validation[:len(Xv)]]
    rts = [day_ahead(target, r) for r in split.validation[:len(Xv)]]
    # NO post-hoc bias: when a Ridge is fit on a feature subset,
    # the bias is already part of the learned relationship.
    corrected = [d_i + pr for d_i, pr in zip(rts, predicted_residual)]
    cand_metrics = _metrics(actuals, corrected)
    base_metrics = _metrics(actuals, rts)
    return {
        "ablation_id": spec.ablation_id,
        "description": spec.description,
        "n_train": len(X),
        "n_validation": len(Xv),
        "features_kept_count": len(keep_cols),
        "constant_bias": bias,
        "candidate_MAE": cand_metrics["MAE"],
        "candidate_RMSE": cand_metrics["RMSE"],
        "candidate_sMAPE_pct": cand_metrics["sMAPE_pct"],
        "baseline_MAE": base_metrics["MAE"],
        "baseline_RMSE": base_metrics["RMSE"],
        "relative_diff_MAE_pct": 100 * (cand_metrics["MAE"] - base_metrics["MAE"]) / max(base_metrics["MAE"], 1e-9),
    }


def run_ablations(out_dir: Path = ABLATION_DIR) -> dict:
    """Run every ablation spec on every (fold, target) combination."""
    out_dir.mkdir(parents=True, exist_ok=True)
    folds = chronological_folds()
    summary = {
        "schema": "stage_11_feature_ablation_v1",
        "ablation_specs": [
            {"ablation_id": s.ablation_id, "description": s.description,
             "use_calendar": s.use_calendar,
             "use_day_ahead": s.use_day_ahead,
             "use_lags": s.use_lags,
             "include_constant_bias": s.include_constant_bias}
            for s in ABLATION_SPECS
        ],
        "folds": [],
        "n_folds": len(folds),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    for fold in folds:
        for target in TARGETS:
            res = {"fold_id": fold.fold_id, "target": target,
                   "n_train": fold.n_train(),
                   "n_validation": fold.n_validation(),
                   "ablations": {}}
            for spec in ABLATION_SPECS:
                a = _evaluate_ridge_with_subset(target, fold, spec)
                res["ablations"][spec.ablation_id] = a
            out_path = out_dir / f"{fold.fold_id}_{target}.json"
            out_path.write_text(json.dumps(res, indent=2, sort_keys=True) + "\n",
                                 encoding="utf-8")
            summary["folds"].append({
                "fold_id": fold.fold_id, "target": target,
                "path": str(out_path.relative_to(out_dir.parent.parent)),
                "A_baseline_MAE": res["ablations"]["A_rts_only"]["candidate_MAE"],
                "B_constant_bias_MAE": res["ablations"]["B_rts_plus_constant_bias"]["candidate_MAE"],
                "C_rts_plus_lag_MAE": res["ablations"]["C_rts_plus_lag"]["candidate_MAE"],
                "D_rts_plus_calendar_MAE": res["ablations"]["D_rts_plus_calendar"]["candidate_MAE"],
                "E_lag_only_MAE": res["ablations"]["E_lag_only"]["candidate_MAE"],
                "F_calendar_only_MAE": res["ablations"]["F_calendar_only"]["candidate_MAE"],
                "G_full_MAE": res["ablations"]["G_full"]["candidate_MAE"],
            })
    summary_path = out_dir / "ablation_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n",
                             encoding="utf-8")
    return summary
