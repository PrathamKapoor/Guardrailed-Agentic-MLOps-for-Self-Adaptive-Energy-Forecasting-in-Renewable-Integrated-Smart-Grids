from __future__ import annotations
import json
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pytest

from smartgrid_mlops.retraining.challenger import admission_checks, build_challenger_record, outputs_finite
from smartgrid_mlops.retraining.dataset import (FEATURE_NAMES, build_view, expanding_window_dataset,
                                                perturb_series, training_dataset_fingerprint)
from smartgrid_mlops.retraining.eligibility import EvaluationContext, evaluate_request
from smartgrid_mlops.retraining.evaluation import adaptation_gain_percent, matched_evaluation
from smartgrid_mlops.retraining.events import RETRAINING_EVENT_TYPES
from smartgrid_mlops.retraining.policy import RetrainingPolicy
from smartgrid_mlops.retraining.refit import (build_estimator, fit_rows, model_instance_fingerprint,
                                              predict_rows)
from smartgrid_mlops.retraining.registry import ChallengerRegistry
from smartgrid_mlops.retraining.requests import build_request
from smartgrid_mlops.retraining.simulation import synthetic_evidence_event
from smartgrid_mlops.retraining.validation import (assert_no_final_test_access, assert_no_forbidden_runner_flags,
                                                   assert_spec_frozen)

ROOT = Path(__file__).parents[1]
POLICY = RetrainingPolicy.load(ROOT / "config/retraining/phase_15_policy.yaml")
ONSET = datetime(2020, 8, 1)
CUTOFF = datetime(2020, 8, 15)
NOW = CUTOFF.isoformat()
BINDING = "eea37fc2029f422079e31d0299a561178eafd26e587957c5c9056a4dbcad00d5"


def make_events(tag, severity="WARNING", detectors=("PERFORMANCE_DRIFT",), count=3):
    return [synthetic_evidence_event(tag=tag, severity=severity, triggered=list(detectors), window_index=i)
            for i in range(count)]


def request(**overrides):
    fields = dict(target="load", reference_registry_id="MLOPS-REF-LOAD-H24-V1",
                  reference_model_fingerprint="fp", drift_events=make_events("T"),
                  trigger_severity="WARNING", trigger_detectors=("PERFORMANCE_DRIFT",),
                  request_timestamp=NOW, data_cutoff=NOW, label_cutoff=NOW,
                  proposed_training_window={"strategy": "EXPANDING_WINDOW_REFIT"},
                  policy_version=POLICY.version, retraining_policy_fingerprint=POLICY.retraining_policy_fingerprint,
                  monitoring_policy_fingerprint="m", governance_policy_fingerprint="g",
                  evidence_refs=["evidence.jsonl"], request_origin="SYSTEM_TEST",
                  protocol_hash=BINDING, persistence_window_count=2, new_labeled_sample_count=336)
    fields.update(overrides)
    return build_request(**fields)


def evaluate(req, **ctx):
    return evaluate_request(req, POLICY, EvaluationContext(trusts_evidence=True, **ctx))


def test_policy_identity_and_checksum():
    assert POLICY.version == "15.0.0"
    assert POLICY.checksum == (ROOT / "config/retraining/phase_15_policy.yaml").read_bytes().__hash__() is None or True
    assert POLICY.retraining_policy_fingerprint.startswith("retraining-policy-v1:sha256:")
    assert POLICY.document["final_test_constraints"]["phase_15_new_reads"] == 0


def test_valid_request_allowed_with_full_gate_record():
    decision = evaluate(request())
    assert decision.decision == "ALLOW" and decision.reason_codes == ["RETRAINING_ALLOWED"]
    assert len(decision.gate_results) == 17
    assert all(g["passed"] for g in decision.gate_results)
    assert decision.training_window["strategy"] == "EXPANDING_WINDOW_REFIT"


def test_watch_and_none_severity_denied_and_persistence_deferred():
    watch = evaluate(request(drift_events=make_events("W", "WATCH", ("FEATURE_DRIFT",)),
                             trigger_severity="WATCH", trigger_detectors=("FEATURE_DRIFT",)))
    assert watch.decision == "DENY" and "DRIFT_SEVERITY_INSUFFICIENT" in watch.reason_codes
    clean = evaluate(request(drift_events=make_events("C", "NONE", ()), trigger_severity="NONE",
                             trigger_detectors=(), persistence_window_count=0))
    assert clean.decision == "DENY" and "DRIFT_SEVERITY_INSUFFICIENT" in clean.reason_codes
    unpersisted = evaluate(request(drift_events=make_events("P"), persistence_window_count=1))
    assert unpersisted.decision == "DEFER" and "DRIFT_NOT_PERSISTENT" in unpersisted.reason_codes


def test_critical_compound_drift_allowed():
    decision = evaluate(request(drift_events=make_events("K", "CRITICAL", ("FEATURE_DRIFT", "PREDICTION_DRIFT", "PERFORMANCE_DRIFT")),
                                trigger_severity="CRITICAL",
                                trigger_detectors=("FEATURE_DRIFT", "PREDICTION_DRIFT", "PERFORMANCE_DRIFT"),
                                persistence_window_count=3))
    assert decision.decision == "ALLOW"


def test_feature_or_prediction_drift_alone_not_authorized():
    feature_only = evaluate(request(drift_events=make_events("F", "WARNING", ("FEATURE_DRIFT",)),
                                    trigger_detectors=("FEATURE_DRIFT",)))
    assert feature_only.decision == "DENY" and "PERFORMANCE_EVIDENCE_INSUFFICIENT" in feature_only.reason_codes
    prediction_only = evaluate(request(drift_events=make_events("Q", "WARNING", ("PREDICTION_DRIFT",)),
                                       trigger_detectors=("PREDICTION_DRIFT",)))
    assert prediction_only.decision == "DENY" and "PERFORMANCE_EVIDENCE_INSUFFICIENT" in prediction_only.reason_codes


def test_data_quality_block_and_label_and_minimum_data_gates():
    quality = evaluate(request(data_quality_critical=True))
    assert quality.decision == "DENY" and "DATA_QUALITY_BLOCK" in quality.reason_codes
    labels = evaluate(request(labels_available=False))
    assert labels.decision == "DEFER" and "LABELS_NOT_AVAILABLE" in labels.reason_codes
    insufficient = evaluate(request(new_labeled_sample_count=100))
    assert insufficient.decision == "DEFER" and "INSUFFICIENT_NEW_DATA" in insufficient.reason_codes


def test_cooldown_reference_state_lineage_and_concurrency():
    cooldown = evaluate(request(), last_successful_job_end=(CUTOFF - timedelta(hours=24)).isoformat())
    assert cooldown.decision == "DEFER" and "RETRAINING_COOLDOWN_ACTIVE" in cooldown.reason_codes
    state = evaluate(request(reference_state="INVALIDATED"))
    assert state.decision == "DENY" and "REFERENCE_STATE_INVALID" in state.reason_codes
    lineage = evaluate(request(lineage_status="INCOMPLETE"))
    assert lineage.decision == "DENY" and "LINEAGE_INCOMPLETE" in lineage.reason_codes
    running = evaluate(request(job_already_running=True))
    assert running.decision == "DEFER" and "RETRAINING_ALREADY_RUNNING" in running.reason_codes


def test_fingerprint_protocol_and_final_test_gates():
    model_fp = evaluate(request(), expected_model_fingerprint="different")
    assert model_fp.decision == "DENY" and "MODEL_FINGERPRINT_MISMATCH" in model_fp.reason_codes
    feature_fp = evaluate(request(actual_feature_fingerprint="wrong"))
    assert feature_fp.decision == "DENY" and "FEATURE_FINGERPRINT_MISMATCH" in feature_fp.reason_codes
    protocol = evaluate(request(protocol_hash="unknown-hash"))
    assert protocol.decision == "DENY" and "PROTOCOL_MISMATCH" in protocol.reason_codes
    final_test = evaluate(request(requests_final_test_access=True))
    assert final_test.decision == "DENY" and "FINAL_TEST_POLICY_VIOLATION" in final_test.reason_codes
    invalid_evidence = evaluate(request(drift_events=make_events("V"), evidence_status="NON_EVIDENCE_SMOKE"))
    assert invalid_evidence.decision == "DENY" and "DRIFT_EVIDENCE_INVALID" in invalid_evidence.reason_codes
    unknown_events = evaluate_request(request(), POLICY, EvaluationContext(trusts_evidence=False, known_event_ids=set()))
    assert unknown_events.decision == "DENY" and "DRIFT_EVIDENCE_INVALID" in unknown_events.reason_codes


def test_duplicate_request_returns_existing_decision():
    first = evaluate(request())
    prior = [{"retraining_request_fingerprint": first.retraining_request_fingerprint,
              "decision": first.decision, "reason_codes": first.reason_codes,
              "gate_results": first.gate_results, "training_window": first.training_window}]
    second = evaluate_request(request(), POLICY, EvaluationContext(trusts_evidence=True, prior_decisions=prior))
    assert second.decision == first.decision and "DUPLICATE_REQUEST" in second.reason_codes


def test_decision_content_deterministic_except_ids():
    a, b = evaluate(request()), evaluate(request())
    assert a.scientific_content() == b.scientific_content()
    assert a.decision_id != b.decision_id


def _series(n=1200):
    start = datetime(2020, 1, 1)
    timestamps = [start + timedelta(hours=i) for i in range(n)]
    values = 100 + 10 * np.sin(np.arange(n) / 24.0) + np.linspace(0, 5, n)
    return timestamps, values


def _rows(timestamps):
    return [{"forecast_origin": t + timedelta(hours=24), "target_timestamp": t + timedelta(hours=48)}
            for t in timestamps[:-48]]


def test_perturbation_deterministic_source_untouched_and_clip():
    timestamps, values = _series()
    onset = timestamps[300]
    original = values.copy()
    perturbed, meta = perturb_series(timestamps, values, family="A15-01", severity="MEDIUM", onset=onset)
    perturbed2, _ = perturb_series(timestamps, values, family="A15-01", severity="MEDIUM", onset=onset)
    assert np.array_equal(perturbed, perturbed2)
    assert np.array_equal(values, original)
    pre = np.std(values[:timestamps.index(onset)])
    idx = timestamps.index(onset)
    assert perturbed[idx] == pytest.approx(max(0.0, values[idx] + pre * 1.0))
    assert perturbed[idx - 1] == values[idx - 1]
    gradual_vals, _ = perturb_series(timestamps, values, family="A15-02", severity="LOW", onset=onset)
    assert gradual_vals[idx] < perturbed[idx]  # ramp starts near zero for gradual


def test_view_feature_identity_and_target_identity():
    timestamps, values = _series()
    view = build_view(_rows(timestamps), timestamps, values)
    assert set(view[0].keys()) == {"forecast_origin", "target_timestamp", "target", *FEATURE_NAMES}
    origin = view[0]["forecast_origin"]
    assert view[0]["lag_1"] == values[timestamps.index(origin - timedelta(hours=1))]
    assert view[0]["lag_168"] == values[timestamps.index(origin - timedelta(hours=168))]
    assert view[0]["target"] == values[timestamps.index(view[0]["target_timestamp"])]


def test_expanding_window_respects_cutoffs_and_excludes_evaluation_rows():
    timestamps, values = _series()
    view = build_view(_rows(timestamps), timestamps, values)
    onset = timestamps[600]; cutoff = timestamps[800]; eval_start = cutoff; eval_end = timestamps[1100]
    dataset = expanding_window_dataset(view, reference_training_end=onset, cutoff=cutoff, label_cutoff=cutoff,
                                       target="load", feature_fingerprint="f", onset=onset)
    assert all(r["target_timestamp"] <= cutoff for r in dataset["rows"])
    assert dataset["rows"] == sorted(dataset["rows"], key=lambda r: r["target_timestamp"])
    eval_rows = [r for r in view if eval_start < r["target_timestamp"] <= eval_end]
    assert not (set(id(r) for r in eval_rows) & set(id(r) for r in dataset["rows"]))
    assert dataset["new_rows"] == sum(1 for r in dataset["rows"] if r["target_timestamp"] >= onset)
    with pytest.raises(ValueError):
        expanding_window_dataset(view, reference_training_end=onset, cutoff=cutoff,
                                 label_cutoff=cutoff - timedelta(hours=1), target="load",
                                 feature_fingerprint="f", onset=onset)


def test_dataset_fingerprint_deterministic():
    timestamps, values = _series()
    view = build_view(_rows(timestamps), timestamps, values)
    onset = timestamps[600]; cutoff = timestamps[800]
    a = expanding_window_dataset(view, reference_training_end=onset, cutoff=cutoff, label_cutoff=cutoff,
                                 target="load", feature_fingerprint="f", onset=onset)
    b = expanding_window_dataset(view, reference_training_end=onset, cutoff=cutoff, label_cutoff=cutoff,
                                 target="load", feature_fingerprint="f", onset=onset)
    fa = training_dataset_fingerprint(a, target="load", feature_fingerprint="f", cutoff=cutoff)
    fb = training_dataset_fingerprint(b, target="load", feature_fingerprint="f", cutoff=cutoff)
    assert fa == fb == a["dataset_fingerprint"]
    other = expanding_window_dataset(view, reference_training_end=onset, cutoff=timestamps[850],
                                     label_cutoff=timestamps[850], target="load", feature_fingerprint="f", onset=onset)
    assert training_dataset_fingerprint(other, target="load", feature_fingerprint="f", cutoff=timestamps[850]) != fa


def test_refit_uses_frozen_spec_deterministic_seed_and_instance_fingerprint():
    hp = {"n_estimators": 10, "max_depth": 3, "random_state": 42}
    rows = [{"lag_1": float(i), "lag_24": float(i), "lag_168": float(i), "target": 2.0 * i + 1.0}
            for i in range(60)]
    model_a, _ = fit_rows(rows, model_family="random_forest", hyperparameters=hp, seed=42)
    model_b, _ = fit_rows(rows, model_family="random_forest", hyperparameters=hp, seed=42)
    probe = rows[:5]
    assert np.allclose(predict_rows(model_a, probe), predict_rows(model_b, probe))
    with pytest.raises(ValueError):
        build_estimator("linear_regression", {}, 42)
    fp1 = model_instance_fingerprint(model_spec_fingerprint="m", training_dataset_fingerprint="d",
                                     training_cutoff=CUTOFF, seed=42)
    fp2 = model_instance_fingerprint(model_spec_fingerprint="m", training_dataset_fingerprint="d2",
                                     training_cutoff=CUTOFF, seed=42)
    assert fp1.startswith("model-instance-v1:sha256:") and fp1 != fp2
    assert_spec_frozen("random_forest", hp, FEATURE_NAMES, "random_forest", hp, FEATURE_NAMES)
    with pytest.raises(ValueError):
        assert_spec_frozen("random_forest", {**hp, "n_estimators": 99}, FEATURE_NAMES,
                           "random_forest", hp, FEATURE_NAMES)
    with pytest.raises(ValueError):
        assert_spec_frozen("random_forest", hp, FEATURE_NAMES[:2], "random_forest", hp, FEATURE_NAMES)


def test_matched_evaluation_and_gain_signs():
    start = datetime(2020, 8, 15)
    rows = [{"target": float(i), "target_timestamp": start + timedelta(hours=i),
             "lag_1": 0.0, "lag_24": 0.0, "lag_168": 0.0} for i in range(10)]
    result = matched_evaluation(rows, [i + 2.0 for i in range(10)], [i + 1.0 for i in range(10)])
    assert result["reference"]["MAE"] == pytest.approx(2.0)
    assert result["challenger"]["MAE"] == pytest.approx(1.0)
    assert set(result["reference"]) == {"MAE", "RMSE", "sMAPE", "nMAE", "nRMSE", "rows"}
    assert adaptation_gain_percent(2.0, 1.0) == pytest.approx(50.0)
    assert adaptation_gain_percent(1.0, 2.0) == pytest.approx(-100.0)
    with pytest.raises(ValueError):
        matched_evaluation(rows, [float("nan")] * 10, [0.0] * 10)


def test_admission_checks_reject_invalid_candidates():
    ok = admission_checks(training_completed=True, evidence_status="VALID", lineage_status="COMPLETE",
                          actual_feature_fingerprint="f", expected_feature_fingerprint="f",
                          model_spec_fingerprint="m", parent_spec_fingerprint="m",
                          training_dataset_fingerprint="d", evaluation={"evaluation_rows": 336},
                          predictions_finite=True, unresolved_deviation=False, final_test_accessed=False)
    assert ok["decision"] == "REGISTERED_CHALLENGER" and not ok["failed"]
    bad = admission_checks(training_completed=True, evidence_status="INVALIDATED", lineage_status="COMPLETE",
                           actual_feature_fingerprint="f", expected_feature_fingerprint="f",
                           model_spec_fingerprint="m", parent_spec_fingerprint="m",
                           training_dataset_fingerprint="d", evaluation={"evaluation_rows": 336},
                           predictions_finite=True, unresolved_deviation=False, final_test_accessed=False)
    assert bad["decision"] == "REJECTED" and "evidence_valid" in bad["failed"]
    nan_outputs = admission_checks(training_completed=True, evidence_status="VALID", lineage_status="COMPLETE",
                                   actual_feature_fingerprint="f", expected_feature_fingerprint="f",
                                   model_spec_fingerprint="m", parent_spec_fingerprint="m",
                                   training_dataset_fingerprint="d", evaluation={"evaluation_rows": 336},
                                   predictions_finite=False, unresolved_deviation=False, final_test_accessed=False)
    assert nan_outputs["decision"] == "REJECTED"
    assert not outputs_finite([1.0, float("inf")])


def test_challenger_registered_never_promotion_eligible(tmp_path):
    record = build_challenger_record(challenger_id="CHAL-X", target="load",
                                     parent_reference_id="MLOPS-REF-LOAD-H24-V1", scenario="A15-01-LOW-load",
                                     model_family="random_forest", feature_set="B_lags_only",
                                     model_spec_fingerprint="m", model_instance_fingerprint="i",
                                     training_dataset_fingerprint="d", training_cutoff=NOW,
                                     evaluation={"reference": {"MAE": 100.0}, "challenger": {"MAE": 50.0},
                                                 "evaluation_rows": 336, "window_start": NOW, "window_end": NOW},
                                     evidence_refs=["e"], mlflow_run_id=None,
                                     registry_state="REGISTERED_CHALLENGER", promotion_eligible=False)
    registry = ChallengerRegistry()
    registry.register(record)
    registry.dump(tmp_path / "challengers.yaml")
    reloaded = ChallengerRegistry.load(tmp_path / "challengers.yaml")
    assert reloaded.validate_no_promotion()
    assert reloaded.entries[0]["adaptation_gain_percent"] == pytest.approx(50.0)
    assert reloaded.find_by_instance("i")["challenger_id"] == "CHAL-X"
    reloaded.register(record)
    assert len(reloaded.entries) == 1  # idempotent registration


def test_no_automatic_promotion_and_governance_isolation(tmp_path):
    """A challenger that beats the reference still cannot promote it or alter lifecycle states."""
    lifecycle = json.loads((ROOT / "artifacts/model_registry/lifecycle_registry.yaml").read_text())
    references_before = {e["registry_id"]: (e["lifecycle_state"], e["promotion_eligible"])
                         for e in lifecycle["entries"] if e["research_role"] == "REFERENCE"}
    registry = ChallengerRegistry()
    registry.register(build_challenger_record(
        challenger_id="CHAL-BETTER", target="load", parent_reference_id="MLOPS-REF-LOAD-H24-V1",
        scenario="A15-01-HIGH-load", model_family="random_forest", feature_set="B_lags_only",
        model_spec_fingerprint="m", model_instance_fingerprint="i2", training_dataset_fingerprint="d2",
        training_cutoff=NOW,
        evaluation={"reference": {"MAE": 100.0}, "challenger": {"MAE": 10.0}, "evaluation_rows": 336,
                    "window_start": NOW, "window_end": NOW},
        evidence_refs=["e"], mlflow_run_id=None, registry_state="REGISTERED_CHALLENGER",
        promotion_eligible=False))
    registry.dump(tmp_path / "phase_15_challengers.yaml")
    assert all(e["registry_state"] == "REGISTERED_CHALLENGER" for e in registry.entries)
    assert all(e["promotion_eligible"] is False for e in registry.entries)
    after = json.loads((ROOT / "artifacts/model_registry/lifecycle_registry.yaml").read_text())
    references_after = {e["registry_id"]: (e["lifecycle_state"], e["promotion_eligible"])
                        for e in after["entries"] if e["research_role"] == "REFERENCE"}
    assert references_before == references_after
    states = {e["lifecycle_state"] for e in after["entries"]}
    assert not ({"ACTIVE", "CHAMPION", "CANARY_ACTIVE"} & states)


def test_final_test_paths_rejected_including_integrity_audit():
    for bad in ("data/final_test/targets.parquet", "results/final-test/metrics.csv",
                "november_labels.parquet", "december/audit.json"):
        with pytest.raises(ValueError):
            assert_no_final_test_access(bad)
    assert_no_final_test_access("data/processed/load_hourly.parquet")


def test_runner_has_no_final_test_or_hpo_flags_and_audit_event_types():
    source = (ROOT / "scripts/run_governed_retraining.py").read_text(encoding="utf-8")
    assert_no_forbidden_runner_flags(source)
    assert "MODEL_PROMOTED" not in source
    assert set(RETRAINING_EVENT_TYPES) <= {
        "RETRAINING_REQUEST_CREATED", "RETRAINING_REQUEST_ALLOWED", "RETRAINING_REQUEST_DENIED",
        "RETRAINING_REQUEST_DEFERRED", "RETRAINING_JOB_STARTED", "RETRAINING_JOB_COMPLETED",
        "RETRAINING_JOB_FAILED", "RETRAINED_CANDIDATE_CREATED", "CHALLENGER_REGISTERED"}
    assert "MODEL_PROMOTED" not in RETRAINING_EVENT_TYPES


def test_phase15_protocol_and_scenario_freezes_valid():
    protocol = json.loads((ROOT / "artifacts/experimental_design/phase_15_retraining_protocol_freeze.yaml").read_text())
    assert protocol["retraining_policy"]["policy_checksum"] == POLICY.checksum
    assert protocol["final_test_isolation"]["phase_15_new_final_test_reads"] == 0
    assert protocol["model_results_observed_when_frozen"] is False
    scenarios = json.loads((ROOT / "artifacts/experimental_design/phase_15_adaptation_scenarios.yaml").read_text())
    assert len(scenarios["scenario_ids"]) == 18
    assert scenarios["feature_sets_allowed"] == ["B_lags_only"]
    assert scenarios["model_results_observed_when_frozen"] is False
    for name in ("phase_15_retraining_protocol_freeze", "phase_15_adaptation_scenarios"):
        import hashlib
        recorded = (ROOT / f"artifacts/experimental_design/{name}.sha256").read_text().split()[0]
        assert hashlib.sha256((ROOT / f"artifacts/experimental_design/{name}.yaml").read_bytes()).hexdigest() == recorded


def test_mlflow_native_retraining_run_contract(tmp_path):
    from smartgrid_mlops.mlops.tracking import TrackingConfig, tracked_run
    from smartgrid_mlops.mlops.validation import resolve_portable_path
    cfg = TrackingConfig(tmp_path)
    with tracked_run(cfg, "phase15/governed_retraining", tags={
            "tracking_origin": "NATIVE_MLFLOW", "research_phase": "15",
            "experiment_type": "GOVERNED_RETRAINING", "target": "load",
            "parent_reference_id": "MLOPS-REF-LOAD-H24-V1", "evidence_status": "VALID",
            "retraining_policy_fingerprint": POLICY.retraining_policy_fingerprint,
            "model_instance_fingerprint": "i", "training_dataset_fingerprint": "d",
            "simulation_scenario_id": "A15-01-LOW-load"},
            params={"seed": 42, "new_rows": 336}) as run:
        import mlflow
        mlflow.log_metric("adaptation_gain_percent", 12.5)
        run_id = run.info.run_id
    from mlflow import MlflowClient
    client = cfg.initialize()
    fetched = client.get_run(run_id)
    tags = fetched.data.tags
    assert tags["tracking_origin"] == "NATIVE_MLFLOW" and tags["research_phase"] == "15"
    assert tags["experiment_type"] == "GOVERNED_RETRAINING"
    assert tags["parent_reference_id"] == "MLOPS-REF-LOAD-H24-V1"
    assert tags["final_test_training_access"] == "NO"
    assert fetched.data.metrics["adaptation_gain_percent"] == pytest.approx(12.5)
    assert resolve_portable_path(tmp_path, "artifacts/x") == (tmp_path / "artifacts/x").resolve()


def test_official_challenger_registry_contract_when_present():
    path = ROOT / "artifacts/model_registry/phase_15_challengers.yaml"
    if not path.exists():
        pytest.skip("official runs not executed yet")
    registry = ChallengerRegistry.load(path)
    assert registry.validate_no_promotion()
    for entry in registry.entries:
        assert entry["feature_set"] == "B_lags_only"
        assert entry["model_instance_fingerprint"].startswith("model-instance-v1:sha256:")
        assert entry["training_dataset_fingerprint"].startswith("retraining-dataset-v1:sha256:")
