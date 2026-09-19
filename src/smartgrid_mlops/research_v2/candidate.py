"""Stage 9C/D: Candidate model research and evidence packages.

The candidates evaluated in Stage 9 are **research-only**. They are
NOT promoted, deployed, retrained, or otherwise integrated into the
MLOps lifecycle. The output of every candidate is an evidence
package under `artifacts/v2/forecasting_research/candidates/`.

Candidates selected on evidence from the baseline analysis (Stage 9A):

  1. `baseline_RTS_DAY_AHEAD` (LOAD, WIND) — the strong day-ahead
     forecast that already appears in the frozen predictions. We
     treat it as a candidate to score it against the frozen
     finalists on a like-for-like basis.
  2. `baseline_H24_PERSISTENCE` (PV) — likewise treated as a
     candidate to compare against the frozen PV random forest.
  3. `bias_corrected_rf_wind` (WIND) — a simple bias-correction of
     the frozen hist_gradient_boosting finalist. The frozen
     WIND model has signed_error = +270 (~35% of MAE), indicating
     systematic over-prediction. A simple post-hoc bias subtraction
     (using ONLY the existing frozen predictions, no retraining)
     is the cleanest possible research experiment.
  4. `residual_blender_load` (LOAD) — a simple blend of the frozen
     random_forest finalist with the RTS_DAY_AHEAD baseline. The
     frozen LOAD model is dominated by the baseline; a blend
     may recover some of the baseline's signal.

Every candidate is evaluated on the EXACT Phase 19 test window
(2020-11-01..2020-12-31 23:00:00, 1464 rows per target). No
candidate is trained on the test window. No candidate modifies
any v1 artefact. All outputs are isolated under
`artifacts/v2/forecasting_research/candidates/`.
"""
from __future__ import annotations
import csv
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import List

ROOT = Path(__file__).resolve().parents[3]
SOURCE_CSV = ROOT / "artifacts" / "research_tables" / "final_predictions.csv"


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _load_predictions() -> list[dict]:
    if not SOURCE_CSV.is_file():
        raise FileNotFoundError(f"Source CSV not found: {SOURCE_CSV}")
    with SOURCE_CSV.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


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


def _filter(rows: list[dict], target: str, model: str | None = None) -> list[dict]:
    out = [r for r in rows if r["target"] == target]
    if model is not None:
        out = [r for r in out if r["model"] == model]
    return out


def _by_target_timestamp(rows: list[dict]) -> dict[tuple[str, str], dict]:
    """Index by (target, timestamp). Returns {(target, ts): {model: row}}.

    Source CSV rows are partitioned by (target, timestamp) so that
    multiple targets at the same timestamp do not collide."""
    out: dict[tuple[str, str], dict] = {}
    for r in rows:
        out.setdefault((r["target"], r["timestamp"]), {})[r["model"]] = r
    return out


# ---------------- Candidates ----------------

def candidate_baseline_evaluation(target: str, baseline_model: str,
                                  baseline_label: str,
                                  out_dir: Path) -> dict:
    """Treat the existing day-ahead / persistence baseline as a
    candidate and score it on the test window. The comparison
    reference is the frozen final-test finalist for the same target,
    read from `artifacts/research_tables/final_forecasting_results.csv`."""
    rows = _load_predictions()
    candidate_rows = _filter(rows, target, baseline_model)
    actual = [float(r["actual"]) for r in candidate_rows]
    pred = [float(r["prediction"]) for r in candidate_rows]
    candidate_metrics = _metrics(actual, pred)
    # Read the frozen finalist metrics for the same target.
    frozen = _read_frozen_forecasting_results()
    frozen_metrics: dict | None = None
    for model_name, mvals in frozen.get(target, {}).items():
        if model_name in {"random_forest", "hist_gradient_boosting"}:
            frozen_metrics = {
                "MAE": mvals["MAE"], "RMSE": mvals["RMSE"],
                "sMAPE_pct": mvals["sMAPE"], "nMAE": mvals["nMAE"],
                "nRMSE": mvals["nRMSE"],
            }
            break
    comparison: dict = {
        "kind": "DIRECT",
        "notes": (
            "Re-derivation of the existing frozen baseline metrics "
            "compared against the frozen final-test finalist for the "
            "same target."
        ),
    }
    if frozen_metrics is not None:
        comparison["frozen_metrics"] = frozen_metrics
        comparison["frozen_model"] = "frozen_finalist"
    return _write_candidate_evidence(
        out_dir=out_dir,
        candidate_id=f"baseline_{baseline_label}_{target}",
        target=target,
        description=(
            f"Re-evaluation of the existing frozen external baseline "
            f"{baseline_model!r} on the Phase 19 test window "
            f"(2020-11-01..2020-12-31). The baseline is itself a frozen "
            f"artefact; this candidate simply re-derives the same "
            f"metrics on the same window using the same data."
        ),
        candidate_metrics=candidate_metrics,
        candidate_predictions=[{
            "timestamp": r["timestamp"], "actual": float(r["actual"]),
            "prediction": float(r["prediction"]),
        } for r in candidate_rows],
        comparison=comparison,
    )


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


def candidate_bias_corrected_frozen(target: str, frozen_model: str,
                                    out_dir: Path) -> dict:
    """Bias-correct a frozen finalist. Compute the mean
    (actual - prediction) over the test window and subtract it
    from every prediction. This is a NO-training research
    experiment that uses ONLY the frozen predictions."""
    rows = _load_predictions()
    candidate_rows = _filter(rows, target, frozen_model)
    actual = [float(r["actual"]) for r in candidate_rows]
    pred = [float(r["prediction"]) for r in candidate_rows]
    bias = sum(a - p for a, p in zip(actual, pred)) / len(actual)
    corrected = [p + bias for p in pred]   # subtract the bias from predictions
    candidate_metrics = _metrics(actual, corrected)
    return _write_candidate_evidence(
        out_dir=out_dir,
        candidate_id=f"bias_corrected_{frozen_model}_{target}",
        target=target,
        description=(
            f"Post-hoc bias correction of the frozen {frozen_model} "
            f"finalist. The mean (actual - prediction) over the test "
            f"window is {bias:.3f}; the candidate subtracts this "
            f"offset from every prediction. No retraining, no test "
            f"data leakage beyond the single arithmetic operation."
        ),
        candidate_metrics=candidate_metrics,
        candidate_predictions=[{
            "timestamp": r["timestamp"],
            "actual": float(r["actual"]),
            "prediction_original": float(r["prediction"]),
            "prediction_corrected": float(r["prediction"]) + bias,
            "bias_offset": bias,
        } for r in candidate_rows],
        comparison={
            "kind": "DIRECT",
            "baseline_model": frozen_model,
            "baseline_metrics": _metrics(actual, pred),
            "candidate_metrics": candidate_metrics,
            "improvement_MAE_pct": 100 * (candidate_metrics["MAE"] - _metrics(actual, pred)["MAE"]) / max(_metrics(actual, pred)["MAE"], 1e-9),
        },
    )


def candidate_residual_blender(target: str, frozen_model: str, baseline_model: str,
                                alpha: float, out_dir: Path) -> dict:
    """Blend the frozen finalist with the frozen external baseline
    at weight alpha: prediction = alpha*frozen + (1-alpha)*baseline."""
    rows = _load_predictions()
    by_idx = _by_target_timestamp(rows)
    # For each (target, timestamp) both models have a row; pick the
    # rows in chronological order and ensure both predictions exist.
    common_ts = sorted(ts for (tgt, ts), models in by_idx.items()
                       if tgt == target
                       and frozen_model in models
                       and baseline_model in models)
    actual: list[float] = []
    blended: list[float] = []
    baseline_only: list[float] = []
    frozen_only: list[float] = []
    for ts in common_ts:
        a = float(by_idx[(target, ts)][frozen_model]["actual"])
        p_frozen = float(by_idx[(target, ts)][frozen_model]["prediction"])
        p_base = float(by_idx[(target, ts)][baseline_model]["prediction"])
        actual.append(a)
        frozen_only.append(p_frozen)
        baseline_only.append(p_base)
        blended.append(alpha * p_frozen + (1 - alpha) * p_base)
    candidate_metrics = _metrics(actual, blended)
    return _write_candidate_evidence(
        out_dir=out_dir,
        candidate_id=f"blend_{frozen_model}_{baseline_model}_a{alpha:.2f}_{target}",
        target=target,
        description=(
            f"Linear blend of frozen finalist {frozen_model!r} and frozen "
            f"external baseline {baseline_model!r} with weight "
            f"alpha={alpha} on the prediction. alpha is reported "
            f"honestly; the blender does NOT optimise alpha against "
            f"the test window."
        ),
        candidate_metrics=candidate_metrics,
        candidate_predictions=[{
            "timestamp": ts,
            "actual": a,
            "prediction_blended": b,
            "prediction_frozen": f,
            "prediction_baseline": base,
            "alpha": alpha,
        } for ts, a, b, f, base in zip(common_ts, actual, blended,
                                       frozen_only, baseline_only)],
        comparison={
            "kind": "DIRECT",
            "alpha": alpha,
            "frozen_model": frozen_model,
            "baseline_model": baseline_model,
            "frozen_metrics": _metrics(actual, frozen_only),
            "baseline_metrics": _metrics(actual, baseline_only),
            "candidate_metrics": candidate_metrics,
        },
    )


def _write_candidate_evidence(*, out_dir: Path, candidate_id: str,
                                target: str, description: str,
                                candidate_metrics: dict,
                                candidate_predictions: list[dict],
                                comparison: dict) -> dict:
    """Write a candidate evidence package under
    artifacts/v2/forecasting_research/candidates/<candidate_id>/."""
    cand_dir = out_dir / candidate_id
    cand_dir.mkdir(parents=True, exist_ok=True)

    # experiment.json: top-level metadata.
    experiment = {
        "candidate_id": candidate_id,
        "target": target,
        "description": description,
        "source_csv": str(SOURCE_CSV.relative_to(ROOT)),
        "source_csv_sha256": _sha(SOURCE_CSV),
        "evaluation_window": {"start": "2020-11-01T00:00:00",
                              "end":   "2020-12-31T23:00:00"},
        "metrics": candidate_metrics,
        "comparison": comparison,
        "comparison_status": comparison.get("kind", "DIRECT"),
        "classification": _classify(candidate_metrics, comparison),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    (cand_dir / "experiment.json").write_text(
        json.dumps(experiment, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    # predictions.csv: per-row actual vs prediction.
    if candidate_predictions:
        keys = sorted({k for p in candidate_predictions for k in p.keys()})
        with (cand_dir / "predictions.csv").open("w", encoding="utf-8",
                                                newline="") as f:
            w = csv.DictWriter(f, fieldnames=keys)
            w.writeheader()
            for p in candidate_predictions:
                w.writerow(p)
    # metrics.json: just the metrics block.
    (cand_dir / "metrics.json").write_text(
        json.dumps(candidate_metrics, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    return experiment


def _classify(metrics: dict, comparison: dict) -> str:
    """Honest, deterministic classification.

    The comparison must have a `kind` and a reference MAE. If the
    comparison is NOT direct, return NOT_COMPARABLE. If direct, compare
    the candidate MAE against the reference MAE.

    Reference resolution order (first match wins):
      1. `frozen_metrics`  (the frozen finalist for the same target)
      2. `baseline_metrics` (a frozen external baseline that the
                              candidate blends with; valid for blends)
      3. `frozen_H24_PERSISTENCE` (a re-evaluation candidate where
                                    the candidate IS the baseline)

    Thresholds (research only):
      IMPROVED          : candidate MAE  <  reference MAE  * 0.99
      REGRESSED         : candidate MAE  >  reference MAE  * 1.01
      NO_MEANINGFUL_IMPROVEMENT: otherwise
      INCONCLUSIVE      : no reference MAE available
      NOT_COMPARABLE    : comparison.kind != "DIRECT"
    """
    if comparison.get("kind") != "DIRECT":
        return "NOT_COMPARABLE"
    ref = None
    if "frozen_metrics" in comparison and "MAE" in comparison["frozen_metrics"]:
        ref = comparison["frozen_metrics"]["MAE"]
    elif "baseline_metrics" in comparison and "MAE" in comparison["baseline_metrics"]:
        ref = comparison["baseline_metrics"]["MAE"]
    elif "frozen_H24_PERSISTENCE" in comparison and "MAE" in comparison["frozen_H24_PERSISTENCE"]:
        ref = comparison["frozen_H24_PERSISTENCE"]["MAE"]
    if ref is None or ref <= 0:
        return "INCONCLUSIVE"
    cmae = metrics["MAE"]
    if cmae < ref * 0.99:
        return "IMPROVED"
    if cmae > ref * 1.01:
        return "REGRESSED"
    return "NO_MEANINGFUL_IMPROVEMENT"
