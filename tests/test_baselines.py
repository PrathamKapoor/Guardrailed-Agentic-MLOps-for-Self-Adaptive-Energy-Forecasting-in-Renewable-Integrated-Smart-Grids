from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pyarrow.parquet as pq
import pytest

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "src"))
from smartgrid_mlops.baselines.base import timestamp_lag_value
from smartgrid_mlops.baselines.evaluation import _eligible, _prediction_rows, run_baseline_evaluation
from smartgrid_mlops.baselines.registry import H1_DAILY, H1_PERSISTENCE, H1_WEEKLY, H24_DAILY, H24_WEEKLY, RTS_DAY_AHEAD
from smartgrid_mlops.baselines.validation import ensure_validation_only
from smartgrid_mlops.experimental_design.metrics import smape


def monotonic():
    start = datetime(2020, 1, 1); return {start + timedelta(hours=i): float(i) for i in range(200)}, start


@pytest.mark.parametrize("definition,lag", [(H1_PERSISTENCE, 1), (H1_DAILY, 24), (H1_WEEKLY, 168), (H24_DAILY, 24), (H24_WEEKLY, 168)])
def test_timestamp_indexed_baselines_use_exact_lag_and_available_source(definition, lag):
    values, start = monotonic(); target = start + timedelta(hours=180); origin = target - timedelta(hours=definition.horizons[0])
    value, source = timestamp_lag_value(values, target, lag, origin)
    assert value == 180.0 - lag and source == target - timedelta(hours=lag) and source <= origin


def test_h24_origin_persistence_equals_daily_seasonal_value():
    values, start = monotonic(); target = start + timedelta(hours=180); origin = target - timedelta(hours=24)
    by_origin, _ = timestamp_lag_value(values, origin + timedelta(hours=24), 24, origin)
    by_target, _ = timestamp_lag_value(values, target, 24, origin)
    assert by_origin == by_target


def test_final_test_is_rejected_and_runner_has_no_test_flag():
    with pytest.raises(PermissionError): ensure_validation_only(datetime(2020, 11, 1))
    assert '"--test"' not in (ROOT / "scripts/run_baseline_experiments.py").read_text()


def test_feature_matrix_target_timestamps_are_the_baseline_eligible_timestamps():
    rows = _prediction_rows("load", 24, H24_DAILY)
    eligible = _eligible("load", 24)
    assert [r["target_timestamp"] for r in rows] == [r["target_timestamp"] for r in eligible]


def test_rts_day_ahead_is_aligned_external_h24_and_pv_zeros_are_retained():
    rows = _prediction_rows("pv", 24, RTS_DAY_AHEAD)
    assert rows and all(r["external_baseline"] for r in rows)
    assert any(r["actual"] == 0 for r in rows)
    assert smape([0, 0], [0, 1]) == 100


def test_predictions_deterministic_schema_and_manifest_checksums():
    # The official artifact is produced by the Phase 6 runner; this test must not overwrite it.
    result = _prediction_rows("load", 24, H24_DAILY); assert result
    path = ROOT / "artifacts/experiments/baselines/phase_06/predictions/baseline_predictions.parquet"
    fields = set(pq.read_schema(path).names)
    assert {"experiment_id", "baseline_id", "target", "horizon", "fold_id", "forecast_origin", "target_timestamp", "actual", "prediction", "absolute_error", "squared_error", "external_baseline"} <= fields
    manifest_path = ROOT / "artifacts/experiments/baselines/phase_06/baseline_experiment_manifest.yaml"; manifest = json.loads(manifest_path.read_text())
    assert manifest["final_test_accessed"] is False
    for relative, checksum in manifest["artifact_checksums"].items(): assert hashlib.sha256((ROOT / relative.replace("\\", "/")).read_bytes()).hexdigest() == checksum
