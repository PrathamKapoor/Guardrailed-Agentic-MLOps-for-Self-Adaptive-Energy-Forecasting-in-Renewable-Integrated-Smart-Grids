#!/usr/bin/env python3
"""Phase 19 final-evaluation engine tests (synthetic data; no repository writes)."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from smartgrid_mlops.experimental_design.protocol import ProtocolAccessError
from smartgrid_mlops.final_evaluation.engine import (
    FrozenPlanIntegrityError,
    authorize_final_evaluation,
    daily_persistence_prediction,
    diebold_mariano,
    evaluate_plan,
    fit_predict_mlp,
    holm_bonferroni,
    test_fold_boundaries as build_test_folds,
    verify_frozen_plan,
    write_results,
)

NOV = [datetime(2020, 11, 1) + timedelta(hours=h) for h in range(24)]


def test_fold_structure_covers_only_locked_test():
    folds = build_test_folds()
    assert [f.fold_id for f in folds] == ["F11", "F12"]
    assert folds[0].eval_start == datetime(2020, 11, 1) and folds[0].training_end_exclusive == datetime(2020, 11, 1)
    assert folds[1].eval_end_exclusive == datetime(2021, 1, 1)
    for fold in folds:
        assert fold.training_end_exclusive <= fold.eval_start
        assert fold.training_start == datetime(2020, 1, 1)


def test_authorization_requires_frozen_configuration():
    with pytest.raises(ProtocolAccessError):
        authorize_final_evaluation(NOV, configuration_frozen=False)


def test_authorization_rejects_outside_partition_even_frozen():
    outside = [datetime(2021, 1, 2)]
    with pytest.raises(ProtocolAccessError):
        authorize_final_evaluation(outside, configuration_frozen=True)
    with pytest.raises(ProtocolAccessError):
        authorize_final_evaluation([datetime(2020, 9, 15)], configuration_frozen=False)


def test_authorization_allows_test_timestamps_when_frozen():
    authorize_final_evaluation(NOV, configuration_frozen=True)
    authorize_final_evaluation([datetime(2020, 12, 31, 23)], configuration_frozen=True)


def _write_plan(root, body=None):
    plan = body or {
        "status": "FROZEN_NOT_EXECUTED",
        "horizon": 24,
        "primary_metric": "MAE",
        "final_test_authorization_required": True,
        "matrix": {},
    }
    path = root / "artifacts/experimental_design/final_test_comparison_plan.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(plan, indent=2).encode()
    path.write_bytes(payload)
    sidecar = path.parent / "final_test_comparison_plan.sha256"
    sidecar.write_text(hashlib.sha256(payload).hexdigest() + "\n")
    return path


def test_verify_frozen_plan_accepts_intact_and_rejects_tampered(tmp_path):
    path = _write_plan(tmp_path)
    assert verify_frozen_plan(path)["status"] == "FROZEN_NOT_EXECUTED"
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(FrozenPlanIntegrityError):
        verify_frozen_plan(path)


def test_verify_frozen_plan_rejects_unknown_status_and_missing_sidecar(tmp_path):
    path = _write_plan(tmp_path, {"status": "SOMEONE_ELSE_STATE"})
    with pytest.raises(FrozenPlanIntegrityError):
        verify_frozen_plan(path)
    (path.parent / "final_test_comparison_plan.sha256").unlink()
    path.unlink()
    path.write_text("{}")
    with pytest.raises(FrozenPlanIntegrityError):
        verify_frozen_plan(path)


def test_daily_persistence_math_and_errors():
    origin_base = datetime(2020, 11, 5)
    actuals = {(origin_base - timedelta(hours=24)): 7.5}
    row = {"target_timestamp": origin_base, "forecast_origin": origin_base - timedelta(hours=24)}
    assert daily_persistence_prediction(actuals, row) == 7.5
    with pytest.raises(KeyError):
        daily_persistence_prediction({}, row)
    bad = {"target_timestamp": origin_base, "forecast_origin": origin_base - timedelta(hours=25)}
    with pytest.raises(ValueError):
        daily_persistence_prediction(actuals, bad)


def test_diebold_mariano_direction_and_degenerate_cases():
    rng = np.random.default_rng(11)
    base = np.abs(rng.normal(size=500))
    worse = base + 0.8
    stat, p = diebold_mariano(worse, base)
    assert stat > 5 and p < 1e-6
    same = base.tolist()
    stat0, p0 = diebold_mariano(same, same)
    assert abs(stat0) < 1e-9 and p0 == 1.0
    with pytest.raises(ValueError):
        diebold_mariano([], [])


def test_holm_bonferroni_step_down():
    decisions = holm_bonferroni({"H_B": 0.04, "H_A": 0.01, "H_C": 0.03}, alpha=0.05)
    assert decisions["H_A"]["reject_null_at_alpha"] is True
    assert decisions["H_C"]["reject_null_at_alpha"] is False
    assert decisions["H_B"]["reject_null_at_alpha"] is False
    assert decisions["H_A"]["holm_threshold"] == pytest.approx(0.05 / 3)
    everything = holm_bonferroni({"X": 0.001, "Y": 0.002}, alpha=0.05)
    assert all(v["reject_null_at_alpha"] for v in everything.values())


def test_mlp_deterministic_for_fixed_seed():
    rng = np.random.default_rng(7)
    train = [{"lag_1": float(x), "lag_24": float(x / 2), "lag_168": 0.1} for x in np.sin(np.arange(200) / 5)]
    y_train = [float(np.sin(i / 5)) for i in range(200)]
    evaluate_rows = train[:20]
    params = {"hidden_width": 8, "dropout": 0.05, "learning_rate": 0.01, "weight_decay": 0.0}
    features = ["lag_1", "lag_24", "lag_168"]
    first, epochs_first = fit_predict_mlp(params, features, train, y_train, evaluate_rows, 42)
    second, _ = fit_predict_mlp(params, features, train, y_train, evaluate_rows, 42)
    assert np.array_equal(first, second) and epochs_first >= 1


def _build_synthetic_workspace(tmp_path, hours=24 * 40):
    start = datetime(2020, 10, 22)
    timestamps = [start + timedelta(hours=h) for h in range(hours)]
    actual = [50.0 + 10.0 * np.sin(i / 6) for i in range(hours)]

    canonical = pa.table(
        {
            "timestamp": pa.array(timestamps),
            "actual_system_load": pa.array(actual, type=pa.float64()),
            "day_ahead_system_load": pa.array([a + ((-1) ** i) * 2.0 for i, a in enumerate(actual)], type=pa.float64()),
        }
    )
    processed = tmp_path / "data/processed/load_hourly.parquet"
    processed.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(canonical, processed)

    feature_rows = []
    for index, ts in enumerate(timestamps):
        if index < 168:
            continue
        feature_rows.append(
            {
                "forecast_origin": ts - timedelta(hours=24),
                "target_timestamp": ts,
                "lag_1": actual[index - 1],
                "lag_24": actual[index - 24],
                "lag_168": actual[index - 168],
            }
        )
    table = pa.table(
        {
            "forecast_origin": pa.array([r["forecast_origin"] for r in feature_rows]),
            "target_timestamp": pa.array([r["target_timestamp"] for r in feature_rows]),
            "lag_1": pa.array([r["lag_1"] for r in feature_rows], type=pa.float64()),
            "lag_24": pa.array([r["lag_24"] for r in feature_rows], type=pa.float64()),
            "lag_168": pa.array([r["lag_168"] for r in feature_rows], type=pa.float64()),
        }
    )
    features_path = tmp_path / "data/processed/features/load/h24/combined_v1.parquet"
    features_path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, features_path)

    ablation_config = {
        "feature_sets": {
            "B_lags_only": ["lag_1", "lag_24", "lag_168"],
            "E_full": ["lag_1", "lag_24", "lag_168"],
        }
    }
    (tmp_path / "config").mkdir(exist_ok=True)
    (tmp_path / "config/ablation").mkdir(exist_ok=True)
    (tmp_path / "config/ablation/phase_10.yaml").write_text(json.dumps(ablation_config))

    freeze_dir = tmp_path / "artifacts/experimental_design"
    freeze_dir.mkdir(parents=True, exist_ok=True)
    (freeze_dir / "phase_10_ablation_protocol_freeze.yaml").write_text(
        json.dumps({"classical_models": {"load": {"model": "random_forest", "hyperparameters": {"n_estimators": 5, "max_depth": 3, "random_state": 42}}}})
    )

    hpo_dir = tmp_path / "artifacts/experiments/hpo/phase_09/best_configs"
    hpo_dir.mkdir(parents=True, exist_ok=True)
    (hpo_dir / "load_pytorch_mlp.yaml").write_text(
        json.dumps({"hyperparameters": {"hidden_width": 8, "dropout": 0.05, "learning_rate": 0.01, "weight_decay": 0.0}})
    )

    plan = {
        "status": "FROZEN_NOT_EXECUTED",
        "horizon": 24,
        "primary_metric": "MAE",
        "final_test_authorization_required": True,
        "matrix": {
            "load": {
                "reference_model": {"candidate_id": "SYN-ref", "feature_set": "B_lags_only"},
                "challengers": [{"candidate_id": "SYN-chal", "feature_set": "E_full"}],
                "baseline_comparator": "RTS_DAY_AHEAD",
            }
        },
    }
    _write_plan(tmp_path, plan)
    return tmp_path


def test_evaluate_plan_end_to_end_synthetic_smoke(tmp_path):
    root = _build_synthetic_workspace(tmp_path)
    results = evaluate_plan(root, targets=("load",), smoke=True)
    assert results["status"] == "NON_EVIDENCE_SMOKE"
    entry = results["targets"]["load"]
    assert set(entry["metrics"]) == {"reference", "challenger", "baseline"}
    for block in entry["metrics"].values():
        assert block["samples"] > 0 and np.isfinite(block["MAE"])
    primary = entry["tests_raw"]["FT-H1-LOAD"]
    assert np.isfinite(primary["dm_statistic"]) and 0.0 <= primary["p_value"] <= 1.0
    assert "holm_decision" in primary

    summary = write_results(root, results, tmp_path / "out")
    assert (tmp_path / "out/predictions/final_test_predictions.parquet").exists()
    assert (tmp_path / "out/metrics/final_test_metrics.csv").exists()
    assert summary["targets"]["load"]["primary_test"]["p_value"] == primary["p_value"]
