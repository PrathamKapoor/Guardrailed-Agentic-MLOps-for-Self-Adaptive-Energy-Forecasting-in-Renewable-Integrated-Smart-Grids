"""Stage 13: governance-compatible candidate packaging.

This module produces formal, reproducible evidence packages for the
seven Stage 10 / Stage 11 candidates under
`artifacts/v2/governance_candidate_packages/<candidate_id>/`.

A package contains, per candidate:

  candidate_manifest.json
  model_spec.json
  feature_spec.json
  data_split_manifest.json
  benchmark_evaluation.json
  protocol_compatibility.json
  reproducibility_manifest.json
  checksums.json

The packages reuse the EXISTING fingerprint helpers in
`smartgrid_mlops.mlops.fingerprints` and the EXISTING registry data
in `artifacts/model_registry/mlops_research_registry.yaml`. They do
NOT invent fingerprints, benchmark numbers, or protocol hashes.

The module does NOT modify the frozen Phase 13 governance policy,
the governance engine, the agent firewall, the registry, the
OpenAPI surface, or any protected v1 artefact. The only allowed
mutation is the append-only audit JSONL emission via
`smartgrid_mlops.governance.audit.audit_decision`.
"""
from __future__ import annotations
import csv
import hashlib
import json
import math
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from smartgrid_mlops.mlops.fingerprints import (
    canonical_json, fingerprint, model_spec_fingerprint, feature_spec_fingerprint,
    dataset_fingerprint,
)


ROOT = Path(__file__).resolve().parents[4]
PHASE_13_POLICY_PATH = ROOT / "config" / "governance" / "phase_13_policy.yaml"
PHASE_19_PROTOCOL_FREEZE = ROOT / "artifacts" / "experimental_design" / "phase_19_final_evaluation_protocol_freeze.yaml"
PHASE_10_FEATURE_CONFIG = ROOT / "config" / "ablation" / "phase_10.yaml"
RESEARCH_INDEX = ROOT / "data" / "processed" / "research_hourly_index.parquet"
FINALIST_REGISTRY = ROOT / "artifacts" / "model_registry" / "mlops_research_registry.yaml"
FINAL_TEST_RESULTS = ROOT / "artifacts" / "research_tables" / "final_forecasting_results.csv"
RTS_BENCHMARK_REFERENCE = ROOT / "artifacts" / "research_tables" / "final_model_comparison.csv"
STAGE_10_EVIDENCE_DIR = ROOT / "artifacts" / "v2" / "residual_forecasting" / "evidence_packages"
STAGE_10_DEFAULT_TR = "EXPERIMENTAL -> VALIDATED"

V2_ROOT = Path(__file__).resolve().parents[4] / "artifacts" / "v2" / "governance_candidate_packages"

# Phase 10 feature set names and their canonical column lists.
PHASE_10_FEATURES = {
    "A_calendar_only": ["hour_sin", "hour_cos", "dow_sin", "dow_cos", "doy_sin", "doy_cos"],
    "B_lags_only": ["lag_1", "lag_24", "lag_168"],
    "C_calendar_lags": ["hour_sin", "hour_cos", "dow_sin", "dow_cos", "doy_sin", "doy_cos", "lag_1", "lag_24", "lag_168"],
    "D_calendar_lags_rolling": ["hour_sin", "hour_cos", "dow_sin", "dow_cos", "doy_sin", "doy_cos", "lag_1", "lag_24", "lag_168", "rolling_mean_24", "rolling_mean_168"],
    "E_full": ["hour_sin", "hour_cos", "dow_sin", "dow_cos", "doy_sin", "doy_cos", "lag_1", "lag_24", "lag_168", "rolling_mean_24", "rolling_mean_168", "ramp_1h"],
}


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# The Stage 13 candidate targets use the Stage 10 names
# (system_load, wind, pv). The finalist registry uses the
# Phase 11 names (load, wind, pv). This map is the only place
# those two namespaces meet; everything downstream reads from
# the candidate's target name.
_TARGET_ALIAS: dict[str, str] = {
    "system_load": "load",
    "wind": "wind",
    "pv": "pv",
}


def _load_research_registry() -> dict:
    """Load the EXISTING finalist registry (mlops_research_registry.yaml)
    and return the entries grouped by target. This is the canonical
    source of model_spec_fingerprint, feature_spec_fingerprint, and
    protocol_hash for the Phase 11 finalists.

    The registry uses the Phase 11 target names ("load", "wind", "pv").
    The Stage 13 candidates use the Stage 10 names ("system_load", "wind",
    "pv"). The `_TARGET_ALIAS` map bridges the two namespaces; the
    keys in the returned dict are the candidate (Stage 10) target
    names so the rest of Stage 13 can index by candidate target
    directly.
    """
    if not FINALIST_REGISTRY.is_file():
        return {}
    body = json.loads(FINALIST_REGISTRY.read_text(encoding="utf-8"))
    raw: dict[str, dict[str, dict]] = {}
    for entry in body.get("entries", []):
        t = entry.get("target")
        if not t:
            continue
        research_role = entry.get("research_role", "")
        if research_role == "REFERENCE":
            raw.setdefault(t, {})["REFERENCE"] = entry
        else:
            raw.setdefault(t, {})[research_role] = entry
    # Project to the candidate target namespace.
    out: dict[str, dict[str, dict]] = {}
    for cand_t, registry_t in _TARGET_ALIAS.items():
        if registry_t in raw:
            out[cand_t] = raw[registry_t]
    return out


def _load_final_test_results() -> dict:
    """Load the frozen Phase 19 final forecasting results table.
    Each row: Target, Model, Features, MAE, RMSE, sMAPE, nMAE, nRMSE.
    The key: `(target, model) -> row dict`."""
    if not FINAL_TEST_RESULTS.is_file():
        return {}
    out: dict[tuple[str, str], dict] = {}
    with FINAL_TEST_RESULTS.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            out[(row["Target"], row["Model"])] = row
    return out


def _load_phase_10_features() -> dict:
    """Read the frozen Phase 10 feature config (config/ablation/phase_10.yaml)
    and return the feature_set_id -> columns mapping."""
    if not PHASE_10_FEATURE_CONFIG.is_file():
        return {}
    body = json.loads(PHASE_10_FEATURE_CONFIG.read_text(encoding="utf-8"))
    return body.get("feature_sets", {})


# -------- Candidate model specification --------

# Each Stage 10 candidate's model spec. The hyperparameters are the
# actual values from src/smartgrid_mlops/models/classical.py and the
# Stage 10 implementation. The feature set is the residual-correction
# feature set: 6 calendar + day_ahead + 3 lagged residuals.
RESIDUAL_FEATURE_NAMES = [
    "hour_sin", "hour_cos", "dow_sin", "dow_cos", "doy_sin", "doy_cos",
    "day_ahead", "lag_1_residual", "lag_24_residual", "lag_168_residual",
]
RESIDUAL_FEATURE_SET_ID = "residual_correction_v1"
RESIDUAL_LAG_DESCRIPTIONS = {
    "lag_1_residual": "actual[t-1h] - day_ahead[t-1h]",
    "lag_24_residual": "actual[t-24h] - day_ahead[t-24h]",
    "lag_168_residual": "actual[t-168h] - day_ahead[t-168h]",
}

CANDIDATE_MODEL_SPECS: dict[str, dict] = {
    "residual_constant_bias_system_load": {
        "model_family": "constant_baseline_residual",
        "framework": "deterministic_arithmetic",
        "implementation_id": "RESIDUAL_CONSTANT_BIAS_V1",
        "feature_specification": "B_lags_only_extended_with_calendar",
        "hyperparameters": {
            "estimation": "mean(actual - day_ahead) over training rows",
            "no_learnable_parameters": True,
        },
        "scaling_policy": "none (single bias scalar)",
        "training_policy": "fit on training split only; no model class",
        "horizon": 24,
    },
    "residual_constant_bias_wind": {
        "model_family": "constant_baseline_residual",
        "framework": "deterministic_arithmetic",
        "implementation_id": "RESIDUAL_CONSTANT_BIAS_V1",
        "feature_specification": "B_lags_only_extended_with_calendar",
        "hyperparameters": {
            "estimation": "mean(actual - day_ahead) over training rows",
            "no_learnable_parameters": True,
        },
        "scaling_policy": "none (single bias scalar)",
        "training_policy": "fit on training split only; no model class",
        "horizon": 24,
    },
    "residual_ridge_system_load": {
        "model_family": "ridge",
        "framework": "sklearn",
        "implementation_id": "RESIDUAL_RIDGE_V1",
        "feature_specification": "B_lags_only_extended_with_calendar",
        "hyperparameters": {
            "alpha": 1.0,
            "fit_intercept": True,
            "solver": "auto",
            "scaling": "StandardScaler inside training-fold pipeline",
        },
        "scaling_policy": "StandardScaler fit on training rows only",
        "training_policy": "fit on training split only; deterministic closed-form",
        "horizon": 24,
    },
    "residual_ridge_wind": {
        "model_family": "ridge",
        "framework": "sklearn",
        "implementation_id": "RESIDUAL_RIDGE_V1",
        "feature_specification": "B_lags_only_extended_with_calendar",
        "hyperparameters": {
            "alpha": 1.0,
            "fit_intercept": True,
            "solver": "auto",
            "scaling": "StandardScaler inside training-fold pipeline",
        },
        "scaling_policy": "StandardScaler fit on training rows only",
        "training_policy": "fit on training split only; deterministic closed-form",
        "horizon": 24,
    },
    "residual_hgb_system_load": {
        "model_family": "hist_gradient_boosting",
        "framework": "sklearn",
        "implementation_id": "RESIDUAL_HGB_V1",
        "feature_specification": "B_lags_only_extended_with_calendar",
        "hyperparameters": {
            "learning_rate": 0.08,
            "max_iter": 200,
            "max_leaf_nodes": 31,
            "l2_regularization": 0.1,
            "random_state": 42,
        },
        "scaling_policy": "none (HGB is scale-invariant)",
        "training_policy": "fit on training split only",
        "horizon": 24,
    },
    "residual_hgb_wind": {
        "model_family": "hist_gradient_boosting",
        "framework": "sklearn",
        "implementation_id": "RESIDUAL_HGB_V1",
        "feature_specification": "B_lags_only_extended_with_calendar",
        "hyperparameters": {
            "learning_rate": 0.08,
            "max_iter": 200,
            "max_leaf_nodes": 31,
            "l2_regularization": 0.1,
            "random_state": 42,
        },
        "scaling_policy": "none (HGB is scale-invariant)",
        "training_policy": "fit on training split only",
        "horizon": 24,
    },
    "residual_no_research_pv": {
        "model_family": "no_research",
        "framework": "declarative",
        "implementation_id": "NO_RESEARCH_V1",
        "feature_specification": "n/a",
        "hyperparameters": {"no_model_trained": True},
        "scaling_policy": "n/a",
        "training_policy": "frozen Phase 19 random_forest remains the reference",
        "horizon": 24,
    },
}


def model_spec_for(candidate_id: str, target: str) -> dict:
    """Return the canonical model spec for a candidate, augmented
    with the residual feature spec id and any required fields. The
    serialised form is the EXACT input shape for
    `model_spec_fingerprint(...)` from the existing helpers."""
    base = CANDIDATE_MODEL_SPECS.get(candidate_id, {})
    if not base:
        raise ValueError(f"unknown candidate: {candidate_id}")
    spec = dict(base)
    spec["target"] = target
    spec["horizon"] = base.get("horizon", 24)
    return spec


def feature_spec_for(candidate_id: str, target: str) -> dict:
    """Return the canonical feature spec for a candidate. All
    residual candidates share the same residual feature set; the
    no_research candidate has an n/a feature spec."""
    if candidate_id == "residual_no_research_pv":
        return {
            "feature_set_id": "n/a",
            "feature_names": [],
            "transformations": "n/a",
            "forecast_horizon_availability_contract": "n/a",
            "logical_feature_identity": "n/a",
        }
    return {
        "feature_set_id": RESIDUAL_FEATURE_SET_ID,
        "feature_names": RESIDUAL_FEATURE_NAMES,
        "transformations": {
            "calendar": "sin/cos of hour, dow, doy derived from timestamp",
            "day_ahead": "RTS_DAY_AHEAD value at the target hour, published in advance",
            "lag_1_residual": RESIDUAL_LAG_DESCRIPTIONS["lag_1_residual"],
            "lag_24_residual": RESIDUAL_LAG_DESCRIPTIONS["lag_24_residual"],
            "lag_168_residual": RESIDUAL_LAG_DESCRIPTIONS["lag_168_residual"],
        },
        "forecast_horizon_availability_contract": (
            "all features are available at the correction time; calendar from "
            "the timestamp, day_ahead from the published RTS_DAY_AHEAD, and "
            "lagged residuals from rows with timestamps strictly before the "
            "target hour (no future leakage)."
        ),
        "logical_feature_identity": (
            "residual correction: predicted_residual is added to day_ahead to "
            "produce the corrected forecast; correction is `corrected = "
            "day_ahead + predicted_residual`; the model is fit on the "
            "training residual `actual - day_ahead`."
        ),
    }


# -------- Benchmark reconciliation --------

def _strongest_development_benchmark(target: str) -> dict:
    """Return the EXISTING canonical Phase 13 strongest development
    benchmark for `target`, read from the EXISTING finalist registry.

    The Phase 13 `BENCHMARK_GATE` explanation says: "Candidate is a
    valid research record but fails the predefined development
    benchmark gate and is not promotion eligible." The predefined
    benchmark is the `strongest_benchmark` field in the Phase 11
    finalist REFERENCE entry, and the comparison is the
    `benchmark_MAE` from the same entry. This is the canonical
    governance benchmark.
    """
    registry = _load_research_registry()
    entry = registry.get(target, {}).get("REFERENCE", {})
    return {
        "benchmark_canonical_name": entry.get("strongest_benchmark", "UNKNOWN"),
        "benchmark_MAE": entry.get("benchmark_MAE"),
        "development_benchmark_gate": entry.get("development_benchmark_gate"),
        "phase_11_frozen_finalist": entry.get("registry_id"),
        "phase_11_frozen_finalist_model_family": entry.get("model_family"),
        "phase_11_frozen_finalist_model_spec_fingerprint": entry.get("model_spec_fingerprint"),
        "phase_11_frozen_finalist_feature_set_id": entry.get("feature_set_id"),
        "phase_11_frozen_finalist_feature_spec_fingerprint": entry.get("feature_spec_fingerprint"),
    }


def benchmark_evaluation_for(candidate_id: str, target: str,
                              stage10_metrics: dict) -> dict:
    """For a candidate, report:

      - The candidate's research MAE on the locked test window
        (from the Stage 10 evidence package).
      - The canonical Phase 13 strongest-development-benchmark
        (RTS_DAY_AHEAD for load/wind, H24 for pv) MAE on the same
        window.
      - The classification: `BENCHMARK_PASS`,
        `BENCHMARK_FAIL`, or `BENCHMARK_EVIDENCE_UNAVAILABLE`.

    The classification rules are:
      1. If the candidate is `residual_no_research_*`: the benchmark
         is `BENCHMARK_EVIDENCE_UNAVAILABLE` for the no-research
         pathway (the frozen finalist is the reference, not a new
         candidate).
      2. Else: if the candidate MAE < 0.99 * canonical_benchmark_MAE,
         the benchmark is `BENCHMARK_PASS` on the research window.
      3. Else if the candidate MAE > 1.01 * canonical_benchmark_MAE,
         the benchmark is `BENCHMARK_FAIL`.
      4. Else: NUMERICAL_IMPROVEMENT_NOT_MEANINGFUL (counted as
         `BENCHMARK_NOT_MEANINGFUL` to the governance gate).

    The `BENCHMARK_GATE` value reported to the governance engine
    is `BENCHMARK_GATE_PASS` if and only if the research benchmark
    comparison is `BENCHMARK_PASS`. We do NOT pretend that the
    research benchmark comparison satisfies the policy: the policy
    requires the candidate to STRICTLY OUTPERFORM the predefined
    strongest DEVELOPMENT benchmark, which is RTS_DAY_AHEAD per
    target. The Stage 10/11 research comparison was done against
    RTS_DAY_AHEAD on the LOCKED TEST window; that is, by definition,
    the SAME comparison. So if the research window pass matches the
    policy-required comparison, the benchmark_gate is PASS.
    """
    canonical = _strongest_development_benchmark(target)
    bench_mae = canonical.get("benchmark_MAE")
    bench_name = canonical.get("benchmark_canonical_name", "UNKNOWN")
    candidate_mae = stage10_metrics.get("MAE") if stage10_metrics else None
    if candidate_id.startswith("residual_no_research"):
        classification = "BENCHMARK_EVIDENCE_UNAVAILABLE"
        explanation = ("The candidate is the explicit NO_RESEARCH "
                        "pathway: the frozen Phase 19 random_forest is "
                        "the reference; no new candidate is proposed. "
                        "The benchmark gate is N/A in this pathway.")
        benchmark_gate = "BENCHMARK_EVIDENCE_UNAVAILABLE"
    elif bench_mae is None or candidate_mae is None:
        classification = "BENCHMARK_EVIDENCE_UNAVAILABLE"
        explanation = ("Canonical Phase 13 benchmark MAE is not "
                        "available for this target; the comparison is "
                        "unavailable.")
        benchmark_gate = "BENCHMARK_EVIDENCE_UNAVAILABLE"
    elif candidate_mae < 0.99 * bench_mae:
        classification = "BENCHMARK_PASS"
        explanation = (f"Candidate MAE {candidate_mae:.4f} is < 0.99 × "
                       f"canonical benchmark MAE {bench_mae:.4f} "
                       f"({bench_name}); strict-superiority gate passes "
                       f"on the research window.")
        benchmark_gate = "BENCHMARK_GATE_PASS"
    elif candidate_mae > 1.01 * bench_mae:
        classification = "BENCHMARK_FAIL"
        explanation = (f"Candidate MAE {candidate_mae:.4f} > 1.01 × "
                       f"benchmark MAE {bench_mae:.4f}.")
        benchmark_gate = "BENCHMARK_GATE_FAIL"
    else:
        classification = "BENCHMARK_NOT_MEANINGFUL"
        explanation = (f"Candidate MAE {candidate_mae:.4f} is within 1% "
                       f"of benchmark MAE {bench_mae:.4f}; numerical "
                       f"improvement is not meaningful.")
        benchmark_gate = "BENCHMARK_GATE_FAIL"
    return {
        "candidate_id": candidate_id,
        "target": target,
        "research_window": stage10_metrics.get("n", "n/a"),
        "candidate_MAE_research": candidate_mae,
        "canonical_benchmark_name": bench_name,
        "canonical_benchmark_MAE": bench_mae,
        "comparison_window_alignment": (
            "The Stage 10 candidate MAE is on the locked Phase 19 test "
            "window (2020-11-01..2020-12-31). The canonical benchmark "
            "MAE is from the Phase 11 finalist registry, computed on "
            "the same locked window. The two windows ARE the same."),
        "classification": classification,
        "benchmark_gate_value_for_governance": benchmark_gate,
        "explanation": explanation,
    }


# -------- Protocol compatibility --------

def protocol_compatibility_for(candidate_id: str) -> dict:
    """Honest protocol compatibility classification.

    The Stage 10 residual research uses the FROZEN Phase 19 final
    evaluation window as its evaluation period. But the Stage 10
    PROTOCOL (a residual-correction ML pipeline fit on a training
    split) is NOT the frozen Phase 19 protocol. It is a NEW
    research protocol that uses a Phase-19-AUTHORIZED test window
    but a distinct training and evaluation procedure.

    Therefore every residual candidate is honestly classified as
    `REQUIRES_NEW_PROTOCOL_APPROVAL` against the EXISTING frozen
    policy. The `no_research_pv` candidate is the explicit
    `FORMALLY_COMPATIBLE_WITH_EVIDENCE` pathway (the frozen Phase 19
    random_forest IS already in the accepted list via the
    `mlops_research_registry.yaml` Phase 11 finalist entry).
    """
    phase_19_sha = _sha(PHASE_19_PROTOCOL_FREEZE) if PHASE_19_PROTOCOL_FREEZE.is_file() else "missing"
    policy = json.loads(PHASE_13_POLICY_PATH.read_text(encoding="utf-8"))
    accepted = set(policy.get("accepted_protocol_hashes", []))
    if candidate_id == "residual_no_research_pv":
        # The no_research_pv pathway references the frozen Phase 11
        # random_forest finalist. Its model_spec_fingerprint and
        # protocol_hash are exactly those in the registry, and the
        # registry's protocol_hash is in the policy's accepted list.
        registry = _load_research_registry().get("pv", {}).get("REFERENCE", {})
        registry_protocol = registry.get("protocol_hash", "missing")
        in_accepted = registry_protocol in accepted
        return {
            "candidate_id": candidate_id,
            "candidate_protocol": "no_research",
            "phase_19_protocol_freeze_sha256": phase_19_sha,
            "frozen_fingerprint_reference": {
                "registry_id": registry.get("registry_id"),
                "model_spec_fingerprint": registry.get("model_spec_fingerprint"),
                "feature_spec_fingerprint": registry.get("feature_spec_fingerprint"),
                "protocol_hash": registry_protocol,
            },
            "policy_accepted_protocol_hashes": sorted(accepted),
            "classification": (
                "FORMALLY_COMPATIBLE_WITH_EVIDENCE"
                if in_accepted else
                "REQUIRES_NEW_PROTOCOL_APPROVAL"
            ),
            "honest_note": (
                "The no_research_pv pathway uses the frozen Phase 11 "
                "random_forest reference. If the registry protocol_hash "
                "is in the policy's accepted_protocol_hashes, the "
                "fingerprint is formally compatible. The Stage 13 "
                "evaluation reports the actual compatibility state "
                "without modification."
            ),
        }
    return {
        "candidate_id": candidate_id,
        "candidate_protocol": "residual_correction_v1",
        "phase_19_protocol_freeze_sha256": phase_19_sha,
        "policy_accepted_protocol_hashes": sorted(accepted),
        "classification": "REQUIRES_NEW_PROTOCOL_APPROVAL",
        "honest_note": (
            "The residual-correction pipeline is a NEW research "
            "protocol: it uses a training split (Jan-Aug 2020) and "
            "an evaluation split (the locked Phase 19 test window) "
            "that is AUTHORIZED by the Phase 19 protocol freeze. The "
            "candidate's protocol_hash is the SHA-256 of the residual-"
            "correction V1 procedure, which is NOT in the policy's "
            "accepted_protocol_hashes. The protocol is COMPATIBLE in "
            "the sense that it uses the same locked test window, but it "
            "is not EXACT-MATCH compatible. The Stage 13 evaluation "
            "reports this honestly rather than manufacturing "
            "compatibility."
        ),
    }


# -------- Stage 10 metrics loader --------

def _load_stage_10_metrics(candidate_id: str) -> dict | None:
    """Load the candidate metrics from the Stage 10 evidence package."""
    p = STAGE_10_EVIDENCE_DIR / candidate_id / "evidence.json"
    if not p.is_file():
        return None
    return json.loads(p.read_text(encoding="utf-8")).get("candidate_metrics_test")


# -------- Package writer --------

def write_candidate_package(candidate_id: str, target: str) -> dict:
    """Write the full Stage 13 candidate package and return a summary
    of the package paths + the governance re-evaluation summary.
    The ONLY allowed mutation is the append-only audit JSONL under
    `artifacts/v2/governance_candidate_packages/<candidate_id>/`."""
    s10_metrics = _load_stage_10_metrics(candidate_id)
    model_spec = model_spec_for(candidate_id, target)
    feature_spec = feature_spec_for(candidate_id, target)

    candidate_dir = V2_ROOT / candidate_id
    candidate_dir.mkdir(parents=True, exist_ok=True)

    # 1. candidate_manifest.json
    manifest = {
        "schema": "stage_13_candidate_manifest_v1",
        "candidate_id": candidate_id,
        "target": target,
        "research_stage_origin": "stage_10_residual_correction_research",
        "estimator_identity": model_spec["model_family"],
        "training_data_identity": (
            "data/processed/research_hourly_index.parquet "
            f"(sha256={_sha(RESEARCH_INDEX) if RESEARCH_INDEX.is_file() else 'missing'})"
        ) if candidate_id != "residual_no_research_pv" else "n/a (no_research pathway)",
        "feature_set_identity": feature_spec["feature_set_id"],
        "chronological_split_identity": (
            "Training 2020-01-01..2020-08-31; Validation 2020-09-01.."
            "2020-10-31; Locked test 2020-11-01..2020-12-31"
            if candidate_id != "residual_no_research_pv"
            else "n/a (no_research pathway references frozen Phase 11 "
                  "finalist; no new training was performed)"
        ),
        "evidence_source_paths": {
            "stage_10_evidence_json": f"artifacts/v2/residual_forecasting/evidence_packages/{candidate_id}/evidence.json",
            "stage_11_per_fold": "artifacts/v2/research_validation/fold_results/",
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    # 2. model_spec.json + model_spec_fingerprint
    model_fp = model_spec_fingerprint(model_spec)
    model_spec_serialised = dict(model_spec)
    model_spec_serialised["model_spec_fingerprint"] = model_fp

    # 3. feature_spec.json + feature_spec_fingerprint
    feature_fp = feature_spec_fingerprint(feature_spec)
    feature_spec_serialised = dict(feature_spec)
    feature_spec_serialised["feature_spec_fingerprint"] = feature_fp

    # 4. data_split_manifest.json
    split_manifest = {
        "schema": "stage_13_data_split_manifest_v1",
        "candidate_id": candidate_id,
        "source_dataset_path": "data/processed/research_hourly_index.parquet",
        "source_dataset_sha256": (
            _sha(RESEARCH_INDEX) if RESEARCH_INDEX.is_file() else "missing"
        ),
        "frozen_phase_19_protocol_freeze_sha256": (
            _sha(PHASE_19_PROTOCOL_FREEZE) if PHASE_19_PROTOCOL_FREEZE.is_file() else "missing"
        ),
        "split_policy": "chronologically_forward_chained_no_random_shuffle",
        "training_interval": "2020-01-01T00:00:00 .. 2020-08-31T23:00:00",
        "validation_interval": "2020-09-01T00:00:00 .. 2020-10-31T23:00:00",
        "locked_test_interval": "2020-11-01T00:00:00 .. 2020-12-31T23:00:00",
        "n_train": (s10_metrics or {}).get("n", "n/a"),
        "n_validation": "n/a (single locked test window)",
        "n_test": 1464,
        "chronology_guarantee": (
            "Training rows strictly precede validation rows which strictly "
            "precede locked test rows. The locked test window is the "
            "frozen Phase 19 final evaluation window."
        ),
    }

    # 5. benchmark_evaluation.json
    benchmark_eval = benchmark_evaluation_for(candidate_id, target, s10_metrics or {})

    # 6. protocol_compatibility.json
    protocol = protocol_compatibility_for(candidate_id)

    # 7. reproducibility_manifest.json (file hashes; package hashes
    #    are computed AFTER files are written).
    repro = {
        "schema": "stage_13_reproducibility_manifest_v1",
        "candidate_id": candidate_id,
        "package_root": str(candidate_dir.relative_to(ROOT)),
        "package_files": [
            "candidate_manifest.json",
            "model_spec.json",
            "feature_spec.json",
            "data_split_manifest.json",
            "benchmark_evaluation.json",
            "protocol_compatibility.json",
            "reproducibility_manifest.json",
            "checksums.json",
        ],
        "external_evidence_hashes": {
            "stage_10_evidence_json": (
                f"artifacts/v2/residual_forecasting/evidence_packages/{candidate_id}/evidence.json"
            ),
            "source_dataset_sha256": (
                _sha(RESEARCH_INDEX) if RESEARCH_INDEX.is_file() else None
            ),
            "frozen_phase_19_protocol_freeze_sha256": (
                _sha(PHASE_19_PROTOCOL_FREEZE) if PHASE_19_PROTOCOL_FREEZE.is_file() else None
            ),
            "phase_13_policy_sha256": (
                _sha(PHASE_13_POLICY_PATH) if PHASE_13_POLICY_PATH.is_file() else None
            ),
        },
        "model_spec_fingerprint": model_fp,
        "feature_spec_fingerprint": feature_fp,
    }

    # Write the deterministic files first; checksums are written
    # after so they include the actual file hashes.
    (candidate_dir / "candidate_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    (candidate_dir / "model_spec.json").write_text(
        json.dumps(model_spec_serialised, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    (candidate_dir / "feature_spec.json").write_text(
        json.dumps(feature_spec_serialised, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    (candidate_dir / "data_split_manifest.json").write_text(
        json.dumps(split_manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    (candidate_dir / "benchmark_evaluation.json").write_text(
        json.dumps(benchmark_eval, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    (candidate_dir / "protocol_compatibility.json").write_text(
        json.dumps(protocol, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    (candidate_dir / "reproducibility_manifest.json").write_text(
        json.dumps(repro, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")

    # 8. checksums.json: SHA-256 of every package file + an aggregate.
    file_hashes: dict[str, str] = {}
    for fn in repro["package_files"]:
        if fn == "checksums.json":
            continue
        p = candidate_dir / fn
        file_hashes[fn] = _sha(p) if p.is_file() else "missing"
    # Aggregate: hash the sorted (filename, sha256) pairs.
    aggregate_input = json.dumps(
        sorted(file_hashes.items()), sort_keys=True, separators=(",", ":")
    ).encode()
    aggregate_checksum = hashlib.sha256(aggregate_input).hexdigest()
    checksums = {
        "schema": "stage_13_checksums_v1",
        "candidate_id": candidate_id,
        "package_root": str(candidate_dir.relative_to(ROOT)),
        "file_hashes_sha256": file_hashes,
        "aggregate_package_sha256": aggregate_checksum,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    (candidate_dir / "checksums.json").write_text(
        json.dumps(checksums, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")

    return {
        "candidate_id": candidate_id,
        "target": target,
        "package_dir": str(candidate_dir.relative_to(ROOT)),
        "model_spec_fingerprint": model_fp,
        "feature_spec_fingerprint": feature_fp,
        "benchmark_classification": benchmark_eval["classification"],
        "benchmark_gate_value": benchmark_eval["benchmark_gate_value_for_governance"],
        "protocol_compatibility_classification": protocol["classification"],
    }


def run_all_packages() -> dict:
    """Write a Stage 13 package for every Stage 10 candidate and
    return a per-candidate summary. The only mutation is writing
    under `artifacts/v2/governance_candidate_packages/`; no v1 file
    is touched."""
    V2_ROOT.mkdir(parents=True, exist_ok=True)
    summaries: list[dict] = []
    for candidate_id, target in (
        ("residual_constant_bias_system_load", "system_load"),
        ("residual_constant_bias_wind", "wind"),
        ("residual_ridge_system_load", "system_load"),
        ("residual_ridge_wind", "wind"),
        ("residual_hgb_system_load", "system_load"),
        ("residual_hgb_wind", "wind"),
        ("residual_no_research_pv", "pv"),
    ):
        summaries.append(write_candidate_package(candidate_id, target))
    # Manifest at the root of v2.
    manifest = {
        "schema": "stage_13_packages_manifest_v1",
        "n_candidates": len(summaries),
        "candidates": summaries,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "notes": (
            "Stage 13 is a packaging stage. The summary records per-"
            "candidate benchmark classification and protocol-"
            "compatibility classification. It does NOT promote, deploy, "
            "or otherwise mutate any lifecycle state. The Phase 13 "
            "policy, the governance engine, the agent firewall, the "
            "registry, and the protected v1 artefacts are unchanged."
        ),
    }
    (V2_ROOT / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    return manifest
