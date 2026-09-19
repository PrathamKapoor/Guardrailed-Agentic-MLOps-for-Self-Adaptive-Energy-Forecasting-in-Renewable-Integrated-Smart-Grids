"""Development-only retraining dataset construction with controlled adaptation perturbations.

The perturbation is a CONTROLLED ADAPTATION / CONCEPT-DRIFT PROXY applied to an
in-development copy of the hourly series; source datasets are never mutated.
Features are rebuilt from the perturbed series so the synthetic world is a
coherent retrainable data-generating process, not just perturbed statistics."""
from __future__ import annotations
import hashlib, json
from datetime import datetime, timedelta
from pathlib import Path
import numpy as np
import pyarrow.parquet as pq
from smartgrid_mlops.mlops.fingerprints import fingerprint
from smartgrid_mlops.monitoring.validation import assert_no_final_test_access

TARGET_COLUMN = {"load": "actual_system_load", "wind": "actual_wind", "pv": "actual_pv"}
HOUR = timedelta(hours=1)
LAGS = (1, 24, 168)
FEATURE_NAMES = ["lag_1", "lag_24", "lag_168"]
SEVERITY_MULTIPLIERS = {"LOW": 0.5, "MEDIUM": 1.0, "HIGH": 2.0}
FINAL_TEST_START = datetime(2020, 11, 1)


def load_hourly_series(root: Path, target: str) -> tuple[list[datetime], np.ndarray]:
    assert_no_final_test_access(f"data/processed/{target}_hourly.parquet")
    file, column = f"{target}_hourly.parquet", TARGET_COLUMN[target]
    table = pq.read_table(root / "data/processed" / file, columns=["timestamp", column])
    timestamps = [t for t in table.column("timestamp").to_pylist() if t < FINAL_TEST_START]
    values = np.asarray(table.column(column).to_pylist()[: len(timestamps)], dtype=float)
    return timestamps, values


def load_feature_rows(root: Path, target: str) -> list[dict]:
    assert_no_final_test_access(f"data/processed/features/{target}/h24/combined_v1.parquet")
    rows = pq.read_table(root / f"data/processed/features/{target}/h24/combined_v1.parquet",
                         filters=[("target_timestamp", "<", FINAL_TEST_START)]).to_pylist()
    return [r for r in rows if r["target_timestamp"] < FINAL_TEST_START]


def perturb_series(timestamps, values, *, family: str, severity: str, onset: datetime, ramp_hours: int = 336):
    """Deterministic target-relationship shift on a development-only copy.

    A15-01 (abrupt): y'(t) = clip(y(t) + m*sigma, min=0 for pv else -inf)
    A15-02 (gradual): shift ramps linearly 0 -> m*sigma over `ramp_hours` from onset.
    sigma is the pre-onset development standard deviation (calibration scale).
    """
    values = np.array(values, dtype=float, copy=True)
    index = {t: i for i, t in enumerate(timestamps)}
    onset_index = index.get(onset)
    if onset_index is None:
        raise ValueError("onset timestamp missing from development series")
    pre = values[:onset_index]
    sigma = float(np.std(pre))
    magnitude = SEVERITY_MULTIPLIERS[severity] * sigma
    non_negative = True  # load/wind/pv are generation/demand quantities; negatives are non-physical
    for i in range(onset_index, len(values)):
        if family == "A15-01":
            fraction = 1.0
        elif family == "A15-02":
            elapsed = (timestamps[i] - onset).total_seconds() / 3600.0
            fraction = min(1.0, elapsed / float(ramp_hours))
        else:
            raise ValueError(f"Unknown adaptation family {family}")
        shifted = values[i] + magnitude * fraction
        values[i] = max(0.0, shifted) if non_negative else shifted
    return values, {"family": family, "severity": severity, "onset": onset.isoformat(),
                    "sigma_pre_onset": sigma, "shift_magnitude": magnitude,
                    "ramp_hours": ramp_hours if family == "A15-02" else 0,
                    "target_domain_constraint": "clipped at zero"}


def build_view(rows, timestamps, values):
    """Rebuild B_lags feature view from a (possibly perturbed) hourly series.

    Row identity (forecast_origin, target_timestamp) is taken from the frozen
    combined_v1 feature table so all views share exactly matched timestamps."""
    index = {t: i for i, t in enumerate(timestamps)}
    view = []
    for r in rows:
        origin, tgt = r["forecast_origin"], r["target_timestamp"]
        features = {}
        for k in LAGS:
            i = index.get(origin - k * HOUR)
            features[f"lag_{k}"] = None if i is None else float(values[i])
        if any(v is None for v in features.values()) or tgt not in index:
            continue
        view.append({"forecast_origin": origin, "target_timestamp": tgt, **features,
                     "target": float(values[index[tgt]])})
    return view


def expanding_window_dataset(view, *, reference_training_end: datetime, cutoff: datetime,
                             label_cutoff: datetime, target: str, feature_fingerprint: str,
                             onset: datetime | None = None):
    """Training rows: target_timestamp <= cutoff AND label observed <= label_cutoff.

    Leakage rules: a row's H24 label is observed at its target timestamp, so only
    rows with target_timestamp <= min(cutoff, label_cutoff) may enter training.
    Evaluation rows (target_timestamp > cutoff) can never appear in training."""
    if label_cutoff < cutoff:
        raise ValueError("label cutoff before data cutoff is inconsistent")
    train = [r for r in view if r["target_timestamp"] <= cutoff and r["target_timestamp"] <= label_cutoff]
    if any(r["target_timestamp"] > cutoff for r in train):
        raise AssertionError("leakage: evaluation-period row entered training")
    train = sorted(train, key=lambda r: r["target_timestamp"])
    historical = [r for r in train if onset is not None and r["target_timestamp"] < onset]
    new = [r for r in train if onset is not None and r["target_timestamp"] >= onset]
    dataset_id = fingerprint({
        "target": target, "feature_fingerprint": feature_fingerprint,
        "first_timestamp": train[0]["target_timestamp"].isoformat() if train else None,
        "last_timestamp": train[-1]["target_timestamp"].isoformat() if train else None,
        "row_count": len(train), "cutoff": cutoff.isoformat(),
        "content_sha256": _content_sha(train),
    }, "retraining-dataset-v1")
    return {"rows": train, "historical_rows": len(historical), "new_rows": len(new),
            "total_rows": len(train), "dataset_fingerprint": dataset_id,
            "first_timestamp": train[0]["target_timestamp"] if train else None,
            "last_timestamp": train[-1]["target_timestamp"] if train else None}


def _content_sha(rows):
    digest = hashlib.sha256()
    for r in rows:
        digest.update(r["target_timestamp"].isoformat().encode())
        digest.update(np.float64(r["target"]).tobytes())
        for name in FEATURE_NAMES:
            digest.update(np.float64(r[name]).tobytes())
    return digest.hexdigest()


def training_dataset_fingerprint(dataset: dict, *, target: str, feature_fingerprint: str, cutoff: datetime) -> str:
    return fingerprint({
        "target": target, "feature_fingerprint": feature_fingerprint,
        "first_timestamp": dataset["first_timestamp"].isoformat(),
        "last_timestamp": dataset["last_timestamp"].isoformat(),
        "row_count": dataset["total_rows"], "cutoff": cutoff.isoformat(),
        "content_sha256": _content_sha(dataset["rows"]),
    }, "retraining-dataset-v1")
