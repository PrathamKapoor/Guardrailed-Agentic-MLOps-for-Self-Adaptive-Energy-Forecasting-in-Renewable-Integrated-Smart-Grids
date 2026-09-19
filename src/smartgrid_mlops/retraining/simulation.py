"""Controlled adaptation simulation: monitoring evidence generation on the
perturbed development copy, plus the frozen request-policy scenario suite.

Phase 14 scenarios perturbed monitoring statistics on synthetic streams without
a coherent retrainable process; Phase 15 therefore defines its own controlled
adaptation scenarios (A15-01/A15-02) with a known drift onset on development-
only copies of the real series."""
from __future__ import annotations
from datetime import datetime, timedelta
from uuid import NAMESPACE_URL, uuid4, uuid5
import numpy as np
from smartgrid_mlops.monitoring.feature_drift import normalized_wasserstein
from smartgrid_mlops.monitoring.performance_drift import performance_signals
from smartgrid_mlops.monitoring.severity import classify_severity
from smartgrid_mlops.monitoring.data_quality import check_quality

HOUR = timedelta(hours=1)
FEATURE_NAMES = ["lag_1", "lag_24", "lag_168"]


def _matrix(rows): return np.asarray([[r[n] for n in FEATURE_NAMES] for r in rows], dtype=float)


def feature_statistic(reference_rows, window_rows) -> float:
    """Max per-feature normalized Wasserstein over the B_lags feature matrix."""
    ref = _matrix(reference_rows); cur = _matrix(window_rows)
    return float(max(normalized_wasserstein(ref[:, i], cur[:, i]) for i in range(ref.shape[1])))


def monitoring_evidence(*, view, reference_rows, predict_fn, onset: datetime,
                        request_time: datetime, window_hours: int = 168,
                        stride_hours: int = 24, threshold: float, scenario_id: str, target: str,
                        reference_model_id: str, threshold_freeze_sha256: str) -> list[dict]:
    """Phase 14 detector logic over consecutive post-onset windows of the
    perturbed view. Reference period is the 3*window_hours immediately before
    onset, mirroring the F01-F03 calibration-period length. Actuals and
    predictions are aligned on H24 forecast rows. Event IDs are deterministic
    (uuid5 over scenario identity) so repeated runs reproduce evidence."""
    window = timedelta(hours=window_hours); stride = timedelta(hours=stride_hours)
    ref_actual = [r["target"] for r in reference_rows]
    ref_pred = [float(x) for x in predict_fn(reference_rows)]
    events = []
    k = 0
    while True:
        start = onset + k * stride
        end = start + window
        if end > request_time:
            break
        rows = [r for r in view if start <= r["forecast_origin"] < end]
        if len(rows) < window_hours:
            break
        quality = check_quality(_matrix(rows))
        fw = feature_statistic(reference_rows, rows)
        cur_pred = [float(x) for x in predict_fn(rows)]
        cur_actual = [r["target"] for r in rows]
        pw = normalized_wasserstein(np.asarray(ref_pred), np.asarray(cur_pred))
        perf = performance_signals(ref_actual, ref_pred, cur_actual, cur_pred)
        triggered = []
        if fw > threshold: triggered.append("FEATURE_DRIFT")
        if pw > threshold: triggered.append("PREDICTION_DRIFT")
        if perf["error_wasserstein"] > threshold or perf["mae_degradation"] > 0: triggered.append("PERFORMANCE_DRIFT")
        if perf["error_wasserstein"] > threshold: triggered.append("ERROR_DISTRIBUTION_DRIFT")
        if quality["critical"]: triggered.append("DATA_QUALITY")
        severity = classify_severity(triggered, quality_critical=quality["critical"], magnitude=fw / max(threshold, 1e-9))
        events.append({
            "event_id": str(uuid5(NAMESPACE_URL, f"{scenario_id}|{target}|{k}")),
            "event_type": "DRIFT_ALERT_RAISED", "target": target,
            "scenario_id": scenario_id, "reference_model_id": reference_model_id,
            "window_index": k, "window_start": start.isoformat(), "window_end": end.isoformat(),
            "detector_family": "MULTI", "severity": severity, "triggered": triggered,
            "signal_values": {"feature_stat": fw, "prediction_stat": float(pw),
                              "performance_stat": perf["error_wasserstein"],
                              "mae_degradation": perf["mae_degradation"]},
            "threshold_freeze_sha256": threshold_freeze_sha256,
            "data_origin": "PHASE_15_ADAPTATION_SCENARIO", "final_test_reads": 0,
        })
        k += 1
    return events


def eligible_events(events, min_severity: str = "WARNING"):
    rank = {"NONE": 0, "WATCH": 1, "WARNING": 2, "CRITICAL": 3}
    return [e for e in events if rank.get(e["severity"], 0) >= rank[min_severity]]


def persistence_count(events) -> int:
    """Consecutive eligible windows ending at the most recent eligible window."""
    rank = {"NONE": 0, "WATCH": 1, "WARNING": 2, "CRITICAL": 3}
    eligible = {e["window_index"] for e in events if rank.get(e["severity"], 0) >= 2}
    if not eligible: return 0
    last = max(eligible); count = 0; k = last
    while k in eligible:
        count += 1; k -= 1
    return count


def max_severity(events) -> str:
    rank = {"NONE": 0, "WATCH": 1, "WARNING": 2, "CRITICAL": 3}
    return max((e["severity"] for e in events), key=lambda s: rank.get(s, 0)) if events else "NONE"


def combined_detectors(events) -> list[str]:
    detectors = set()
    for e in events: detectors.update(e["triggered"])
    return sorted(detectors - {"DATA_QUALITY"})


def synthetic_evidence_event(tag: str = "REQPOLICY", **overrides) -> dict:
    severity = overrides.get("severity", "WARNING")
    triggered = overrides.get("triggered", ["PERFORMANCE_DRIFT"])
    window_index = overrides.get("window_index", 0)
    event_id = str(uuid5(NAMESPACE_URL, f"{tag}|{severity}|{','.join(triggered)}|{window_index}"))
    base = {"event_id": event_id, "event_type": "DRIFT_ALERT_RAISED", "target": "load",
            "scenario_id": "REQUEST_POLICY_SIM", "reference_model_id": "MLOPS-REF-LOAD-H24-V1",
            "window_index": window_index, "window_start": "DEVELOPMENT_ONLY", "window_end": "DEVELOPMENT_ONLY",
            "detector_family": "MULTI", "severity": severity, "triggered": triggered,
            "signal_values": {"feature_stat": 0.5, "prediction_stat": 0.1, "performance_stat": 0.5,
                              "mae_degradation": 50.0},
            "threshold_freeze_sha256": "REQUEST_POLICY_SIM", "data_origin": "REQUEST_POLICY_SIMULATION",
            "final_test_reads": 0}
    base.update(overrides)
    return base
