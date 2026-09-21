from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from smartgrid_mlops.external_validation.spec import ExternalValidationSpec
from smartgrid_mlops.external_validation.validation import (
    DatasetNotAvailableError,
    FeatureCompatibilityError,
    FrozenModelError,
    ProvenanceError,
    TemporalCoverageError,
    validate_dataset_manifest,
    validate_feature_compatibility,
    validate_frozen_model,
    validate_no_leakage,
    validate_provenance,
    validate_temporal_coverage,
)
from smartgrid_mlops.external_validation.engine import check_dataset_available, evaluate_external, write_external_results


def _manifest_dict():
    return {
        "source": "https://example.com/dataset.zip",
        "license": "CC-BY-4.0",
        "retrieval_date": "2026-08-26",
        "version": "v1",
        "schema": {"columns": ["timestamp", "actual_system_load"]},
        "approval": "approved",
        "archive_checksum": "a" * 64,
    }


def test_manifest_validation_requires_fields(tmp_path: Path):
    p = tmp_path / "m.json"
    p.write_text(json.dumps({"source": "x"}))
    with pytest.raises(ProvenanceError):
        validate_dataset_manifest(p)
    p.write_text(json.dumps(_manifest_dict()))
    assert validate_dataset_manifest(p)["source"].startswith("https")


def test_manifest_missing_raises_not_available(tmp_path: Path):
    with pytest.raises(DatasetNotAvailableError):
        validate_dataset_manifest(tmp_path / "no.json")


def test_provenance_checksum_required():
    with pytest.raises(ProvenanceError):
        validate_provenance({k: v for k, v in _manifest_dict().items() if k != "archive_checksum"})
    validate_provenance(_manifest_dict())


def test_temporal_coverage_conclusive_and_inconclusive():
    base = datetime(2020, 6, 1)
    hourly = [base + timedelta(hours=i) for i in range(800)]
    info = validate_temporal_coverage(hourly)
    assert info["conclusive"] is True
    short = hourly[:100]
    info2 = validate_temporal_coverage(short)
    assert info2["conclusive"] is False


def test_temporal_missing_fraction():
    base = datetime(2020, 6, 1)
    # 100h span (0..99) with 20 missing, keeping endpoints 0 and 99
    missing_idx = {1, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95}
    ts = [base + timedelta(hours=i) for i in range(100) if i not in missing_idx]
    info = validate_temporal_coverage(ts, min_samples=10)
    assert info["samples"] == 80
    assert info["missing_hours"] == 20
    assert info["missing_fraction"] == pytest.approx(0.2)


def test_feature_compatibility():
    validate_feature_compatibility(["lag_1", "lag_24", "lag_168"], ["lag_1", "lag_24"])
    with pytest.raises(FeatureCompatibilityError):
        validate_feature_compatibility(["lag_1"], ["lag_1", "lag_24"])


def test_frozen_model_enforcement():
    frozen = {"model": "random_forest", "feature_set": "B_lags_only"}
    validate_frozen_model({"model": "random_forest", "feature_set": "B_lags_only"}, frozen)
    with pytest.raises(FrozenModelError):
        validate_frozen_model({"model": "mlp", "feature_set": "B_lags_only"}, frozen)


def test_no_leakage_horizon_enforcement():
    origin = datetime(2020, 6, 1)
    target = origin + timedelta(hours=24)
    rows = [{"forecast_origin": origin, "target_timestamp": target, "lag_1": 1.0}]
    validate_no_leakage(rows)
    bad = [{"forecast_origin": origin, "target_timestamp": origin + timedelta(hours=23)}]
    with pytest.raises(FeatureCompatibilityError if False else Exception):
        validate_no_leakage(bad)


def test_no_leakage_target_after_origin():
    origin = datetime(2020, 6, 1, 12)
    target = datetime(2020, 6, 1, 11)
    with pytest.raises(Exception):
        validate_no_leakage([{"forecast_origin": origin, "target_timestamp": target}])


def test_check_dataset_available_blocker(tmp_path: Path):
    with pytest.raises(DatasetNotAvailableError) as exc:
        check_dataset_available(tmp_path, "nope")
    assert "manifest" in str(exc.value).lower()


def test_evaluate_external_blocker_when_no_dataset(tmp_path: Path):
    # create minimal protocol artifacts to pass frozen plan check? We'll use real root for that part,
    # but with tmp_path no dataset should still blocker
    with pytest.raises(DatasetNotAvailableError):
        evaluate_external(ROOT, "nonexistent_dataset_xyz", targets=("load",), smoke=True)


def test_evaluate_external_smoke_synthetic(tmp_path: Path):
    # Build minimal external dataset under tmp_path/data/processed/external/synth/...
    import hashlib

    root = tmp_path
    # Need to replicate frozen plan and configs from real repo into tmp for evaluate_external to succeed
    import shutil

    real = ROOT
    for src in [
        real / "artifacts/experimental_design/final_test_comparison_plan.yaml",
        real / "artifacts/experimental_design/final_test_comparison_plan.sha256",
        real / "artifacts/experimental_design/phase_10_ablation_protocol_freeze.yaml",
        real / "config/ablation/phase_10.yaml",
    ]:
        dst = root / src.relative_to(real)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(src, dst)
    for src in (real / "artifacts/experiments/hpo/phase_09/best_configs").glob("*.yaml"):
        dst = root / src.relative_to(real)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(src, dst)
    # create manifest
    manifest = _manifest_dict()
    manifest["source"] = "synthetic"
    mpath = root / "data/manifests/synth_manifest.yaml"
    mpath.parent.mkdir(parents=True, exist_ok=True)
    import yaml

    mpath.write_text(yaml.safe_dump(manifest))
    # create external actual and feature artifacts
    import numpy as np

    base = datetime(2020, 7, 1)
    n = 400
    timestamps = [base + timedelta(hours=i) for i in range(n)]
    actual = [50 + 10 * np.sin(i / 6) for i in range(n)]
    # actual parquet
    actual_path = root / "data/processed/external/synth/load_hourly.parquet"
    actual_path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.table({"timestamp": pa.array(timestamps), "actual_system_load": pa.array(actual)}), actual_path)
    # feature parquet: need all 12 features for B_lags_only + E_full compatibility
    import math as _math

    rows = []
    for i, ts in enumerate(timestamps):
        if i < 168:
            continue
        origin = ts - timedelta(hours=24)
        # calendar from origin
        hour = origin.hour
        dow = origin.weekday()
        doy = origin.timetuple().tm_yday
        rows.append(
            {
                "forecast_origin": origin,
                "target_timestamp": ts,
                "hour_sin": _math.sin(2 * _math.pi * hour / 24),
                "hour_cos": _math.cos(2 * _math.pi * hour / 24),
                "dow_sin": _math.sin(2 * _math.pi * dow / 7),
                "dow_cos": _math.cos(2 * _math.pi * dow / 7),
                "doy_sin": _math.sin(2 * _math.pi * doy / 366),
                "doy_cos": _math.cos(2 * _math.pi * doy / 366),
                "lag_1": actual[i - 1],
                "lag_24": actual[i - 24],
                "lag_168": actual[i - 168],
                "rolling_mean_24": sum(actual[i - 24 : i]) / 24,
                "rolling_mean_168": sum(actual[i - 168 : i]) / 168,
                "ramp_1h": actual[i] - actual[i - 1],
            }
        )
    feat_path = root / "data/processed/external/synth/features/load/h24/combined_v1.parquet"
    feat_path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(
        pa.table(
            {
                "forecast_origin": pa.array([r["forecast_origin"] for r in rows]),
                "target_timestamp": pa.array([r["target_timestamp"] for r in rows]),
                "hour_sin": pa.array([r["hour_sin"] for r in rows]),
                "hour_cos": pa.array([r["hour_cos"] for r in rows]),
                "dow_sin": pa.array([r["dow_sin"] for r in rows]),
                "dow_cos": pa.array([r["dow_cos"] for r in rows]),
                "doy_sin": pa.array([r["doy_sin"] for r in rows]),
                "doy_cos": pa.array([r["doy_cos"] for r in rows]),
                "lag_1": pa.array([r["lag_1"] for r in rows]),
                "lag_24": pa.array([r["lag_24"] for r in rows]),
                "lag_168": pa.array([r["lag_168"] for r in rows]),
                "rolling_mean_24": pa.array([r["rolling_mean_24"] for r in rows]),
                "rolling_mean_168": pa.array([r["rolling_mean_168"] for r in rows]),
                "ramp_1h": pa.array([r["ramp_1h"] for r in rows]),
            }
        ),
        feat_path,
    )
    res = evaluate_external(root, "synth", targets=("load",), smoke=True)
    assert res["status"] == "NON_EVIDENCE_SMOKE"
    assert "load" in res["targets"]
    dest = root / "artifacts/experiments/external_validation/synth/smoke"
    write_external_results(root, res, dest)
    assert (dest / "metrics/summary.json").exists()


def test_write_external_results(tmp_path: Path):
    res = {"status": "EXTERNAL_VALIDATION_VALID", "dataset": "x", "generated_at": "now", "targets": {"load": {"metrics": {"a": {"MAE": 1.0, "samples": 10}}, "samples": 10}}}
    dest = tmp_path / "out"
    write_external_results(tmp_path, res, dest)
    assert (dest / "metrics/external_metrics.csv").exists()
