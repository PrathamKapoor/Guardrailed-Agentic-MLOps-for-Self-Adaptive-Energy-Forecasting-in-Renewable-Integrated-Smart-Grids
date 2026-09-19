"""Stage 10: evidence packages and per-target residual research.

This module runs the three candidate strategies
(constant_bias / ridge / hgb) for the targets that the Stage 10E
strategy identifies as candidates for residual research, and writes
an evidence package per candidate under
`artifacts/v2/residual_forecasting/evidence_packages/<candidate_id>/`.

Per-target strategy:

  - LOAD  : residual research is JUSTIFIED. The training residual
            mean is -126 (RTS_DAY_AHEAD is biased by 10% of the
            typical load value). Even a constant-bias correction
            should be MEANINGFUL_IMPROVEMENT.
  - WIND  : residual research is JUSTIFIED. The training residual
            std is huge (~465) relative to the bias (-58). A
            constant bias is not enough; a feature-based residual
            model MIGHT help.
  - PV    : NO RESIDUAL RESEARCH REQUIRED. The frozen Phase 19
            random_forest (MAE=36.12) beats the external H24
            baseline (MAE=39.10) by 7.61%. A constant-bias
            correction of H24 (bias=-22.5) REGRESSES H24 from
            MAE=39.10 to MAE=61.28 (+57%) because the H24
            residual is heavily right-skewed (median=0, mean=-22).
            The frozen RF is the strongest available predictor on
            this target. Stage 10 emits a `NO_RESIDUAL_RESEARCH`
            evidence package for PV with this finding.

Every evidence package is a research classification only. It
contains no field that pretends the research result is a
governance decision.
"""
from __future__ import annotations
import hashlib
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .data import (
    Split, TARGETS, chronological_split, _sha, _metrics,
    residual_summary, day_ahead, actual_value,
)
from .features import (
    ResidualCandidateResult,
    evaluate_constant_bias, evaluate_ridge_residual, evaluate_hgb_residual,
)


V2_ROOT = Path(__file__).resolve().parents[4] / "artifacts" / "v2" / "residual_forecasting"
EVIDENCE_DIR = V2_ROOT / "evidence_packages"
SOURCE_PARQUET = Path(__file__).resolve().parents[4] / "data" / "processed" / "research_hourly_index.parquet"


def _classify_no_research(target: str, split: Split) -> ResidualCandidateResult:
    """The PV `NO_RESIDUAL_RESEARCH` evidence package. The frozen
    Phase 19 random_forest beats the external H24 baseline on
    TEST (36.12 vs 39.10). A residual correction of H24 would
    regress the baseline. We document this rather than fit a
    model on data the protocol says is the wrong target."""
    test_rts_metrics = _metrics(
        [actual_value(target, r) for r in split.test],
        [day_ahead(target, r) for r in split.test],
    )
    return ResidualCandidateResult(
        candidate_id=f"residual_no_research_{target}",
        target=target,
        description=(
            f"NO_RESEARCH. The frozen Phase 19 random_forest "
            f"(MAE=36.12) beats the external baseline (H24 MAE=39.10) "
            f"on the locked test window. A constant-bias correction "
            f"of H24 regresses the baseline by ~57% because the H24 "
            f"residual is right-skewed (median=0, mean=-22). The "
            f"frozen RF is the strongest available predictor on this "
            f"target. Stage 10 emits this as evidence of NO residual "
            f"research required for {target}."
        ),
        feature_set=[],
        n_train=0,
        n_validation=0,
        n_test=split.n_test(),
        training_residual_mean=float("nan"),
        training_residual_std=float("nan"),
        validation={"n": 0, "rts_day_ahead_metrics": {}, "corrected_metrics": {}},
        test={"n": split.n_test(), "rts_day_ahead_metrics": test_rts_metrics,
              "corrected_metrics": {}},
        baseline_metrics_test=test_rts_metrics,
        candidate_metrics_test={},
        classification="NO_RESEARCH_REQUIRED",
        notes="Honest negative result. The frozen RF already wins; "
              "residual correction has no defensible target here.",
    )


def _write_evidence(result: ResidualCandidateResult, split: Split) -> Path:
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    out_dir = EVIDENCE_DIR / result.candidate_id
    out_dir.mkdir(parents=True, exist_ok=True)
    # Build the evidence package. asdict() of a frozen dataclass is
    # not directly supported; we use __dict__.
    body = result.__dict__.copy()
    body["evidence_package"] = {
        "schema": "stage_10_residual_evidence_v1",
        "candidate_id": result.candidate_id,
        "target": result.target,
        "evaluation_window": {
            "start": "2020-11-01T00:00:00",
            "end":   "2020-12-31T23:00:00",
        },
        "training_window": {
            "start": "2020-01-01T00:00:00",
            "end":   "2020-08-31T23:00:00",
        },
        "validation_window": {
            "start": "2020-09-01T00:00:00",
            "end":   "2020-10-31T23:00:00",
        },
        "split_counts": {
            "n_train": split.n_train(),
            "n_validation": split.n_validation(),
            "n_test": split.n_test(),
        },
        "source": {
            "path": str(SOURCE_PARQUET),
            "sha256": _sha(SOURCE_PARQUET),
        },
        "comparison_validity": "DIRECT" if result.baseline_metrics_test and result.candidate_metrics_test else "NOT_COMPARABLE",
        "research_classification": result.classification,
        "absolute_diff_MAE": (
            (result.candidate_metrics_test.get("MAE", float("nan"))
             - result.baseline_metrics_test.get("MAE", float("nan")))
            if result.candidate_metrics_test else None
        ),
        "relative_diff_MAE_pct": (
            100 * (result.candidate_metrics_test.get("MAE", float("nan"))
                   - result.baseline_metrics_test.get("MAE", float("nan")))
                 / max(result.baseline_metrics_test.get("MAE", 1e-9), 1e-9)
            if result.candidate_metrics_test else None
        ),
        "comparison_status": "RESEARCH_CLASSIFICATION_NOT_GOVERNANCE_DECISION",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    out_path = out_dir / "evidence.json"
    out_path.write_text(json.dumps(body, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")
    return out_path


def run_target_research(target: str, split: Split) -> list[Path]:
    """Run the candidate strategies for the given target. For PV we
    short-circuit to a single NO_RESEARCH_REQUIRED evidence
    package. For LOAD and WIND we run the three candidates."""
    out: list[Path] = []
    if target == "pv":
        out.append(_write_evidence(_classify_no_research(target, split), split))
        return out
    # LOAD and WIND: run all three strategies.
    for result in (
        evaluate_constant_bias(target, split),
        evaluate_ridge_residual(target, split),
        evaluate_hgb_residual(target, split),
    ):
        out.append(_write_evidence(result, split))
    return out


def run_all() -> dict:
    """Run the per-target residual research. Returns a manifest
    summarising every evidence package written."""
    split = chronological_split()
    all_paths: list[str] = []
    for target in TARGETS:
        for p in run_target_research(target, split):
            all_paths.append(str(p))
    manifest = {
        "stage": "10",
        "evaluation_window": {
            "start": "2020-11-01T00:00:00",
            "end":   "2020-12-31T23:00:00",
        },
        "training_window": {
            "start": "2020-01-01T00:00:00",
            "end":   "2020-08-31T23:00:00",
        },
        "validation_window": {
            "start": "2020-09-01T00:00:00",
            "end":   "2020-10-31T23:00:00",
        },
        "n_evidence_packages": len(all_paths),
        "evidence_paths": all_paths,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "notes": (
            "Research classifications only. No field in any evidence "
            "package represents a lifecycle decision. The Stage 10 "
            "report (reports/productization/stage_10_completion.md) "
            "is the human-readable summary; the evidence packages "
            "are the machine-readable record."
        ),
    }
    out = EVIDENCE_DIR / "manifest.json"
    out.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                   encoding="utf-8")
    return manifest
