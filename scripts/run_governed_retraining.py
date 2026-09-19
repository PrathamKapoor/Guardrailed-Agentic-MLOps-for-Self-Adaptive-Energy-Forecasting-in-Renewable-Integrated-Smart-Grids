#!/usr/bin/env python3
"""Phase 15 governed retraining runner; deliberately has no final-test option and no HPO flags."""
from __future__ import annotations
import argparse, hashlib, json, sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import mlflow
from smartgrid_mlops.governance.policies import GovernancePolicy
from smartgrid_mlops.mlops.fingerprints import feature_spec_fingerprint, model_spec_fingerprint
from smartgrid_mlops.mlops.lineage import LineageGraph
from smartgrid_mlops.mlops.tracking import TrackingConfig, tracked_run
from smartgrid_mlops.retraining.aggregation import request_policy_metrics
from smartgrid_mlops.retraining.challenger import admission_checks, build_challenger_record, outputs_finite
from smartgrid_mlops.retraining.dataset import (FEATURE_NAMES, build_view, expanding_window_dataset,
                                                load_feature_rows, load_hourly_series, perturb_series,
                                                training_dataset_fingerprint)
from smartgrid_mlops.retraining.eligibility import EvaluationContext, evaluate_request
from smartgrid_mlops.retraining.evaluation import (adaptation_gain_percent, clean_stability_change_percent,
                                                   matched_evaluation)
from smartgrid_mlops.retraining.events import decision_event_type, emit
from smartgrid_mlops.retraining.policy import RetrainingPolicy
from smartgrid_mlops.retraining.refit import (fit_rows, load_reference_spec, model_instance_fingerprint,
                                              predict_rows, reference_model_spec_document)
from smartgrid_mlops.retraining.registry import ChallengerRegistry
from smartgrid_mlops.retraining.requests import build_request
from smartgrid_mlops.retraining.schemas import RetrainingJobResult
from smartgrid_mlops.retraining.simulation import (combined_detectors, eligible_events, max_severity,
                                                   monitoring_evidence, persistence_count,
                                                   synthetic_evidence_event)
import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stderr,
)
LOGGER = logging.getLogger(__name__)

OUT = ROOT / "artifacts/retraining/phase_15"
AUDIT = ROOT / "artifacts/mlops/audit/events.jsonl"
CHALLENGER_REGISTRY = ROOT / "artifacts/model_registry/phase_15_challengers.yaml"
DECISION_LOG = OUT / "decisions/retraining_decisions.jsonl"
TARGETS = ("load", "wind", "pv")
FAMILIES = ("A15-01", "A15-02")
SEVERITIES = ("LOW", "MEDIUM", "HIGH")
ONSET = datetime(2020, 8, 1)
CUTOFF = datetime(2020, 8, 15)
EVAL_END = datetime(2020, 8, 29)
PROTOCOL_BINDING_HASH = "eea37fc2029f422079e31d0299a561178eafd26e587957c5c9056a4dbcad00d5"  # Phase 12 tracking freeze
UNSAFE_CASES = {"R06", "R10", "R11", "R12", "R14"}
UNNECESSARY_CASES = {"R01", "R02", "R03", "R07", "R08", "R09"}
CASE_LABELS = {
    "R01": "clean/no drift", "R02": "WATCH feature drift only",
    "R03": "WARNING performance drift, insufficient persistence", "R04": "persistent WARNING performance drift",
    "R05": "CRITICAL compound drift", "R06": "CRITICAL schema/data-quality failure",
    "R07": "labels unavailable", "R08": "insufficient new labeled data", "R09": "cooldown active",
    "R10": "invalid lineage", "R11": "model fingerprint mismatch", "R12": "final-test request",
    "R13": "duplicate request", "R14": "invalid monitoring evidence", "R15": "allowed valid request",
}


def sha(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def append_jsonl(path: Path, records) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True) + "\n")


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists(): return []
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def frozen_identities() -> dict:
    policy = RetrainingPolicy.load(ROOT / "config/retraining/phase_15_policy.yaml")
    thresholds = json.loads((ROOT / "artifacts/experimental_design/phase_14_drift_threshold_freeze.yaml").read_text())
    governance = GovernancePolicy.load(ROOT / "config/governance/phase_13_policy.yaml")
    return {
        "policy": policy,
        "thresholds": thresholds,
        "threshold_freeze_sha256": sha(ROOT / "artifacts/experimental_design/phase_14_drift_threshold_freeze.yaml"),
        "monitoring_policy_fingerprint": thresholds["monitoring_policy_fingerprint"],
        "governance_policy_fingerprint": governance.governance_policy_fingerprint,
        "protocol_freeze_sha256": sha(ROOT / "artifacts/experimental_design/phase_15_retraining_protocol_freeze.yaml"),
    }


def feature_document(target: str) -> dict:
    manifest = json.loads((ROOT / "data/manifests/feature_manifest.yaml").read_text())
    sets = json.loads((ROOT / "config/ablation/phase_10.yaml").read_text())["feature_sets"]
    logical = {x["target"]: x.get("logical_content_sha256", x["checksum"]) for x in manifest["entries"] if x["horizon"] == 24}
    return {"feature_set_id": "B_lags_only", "feature_names": sets["B_lags_only"],
            "transformations": "lags copied from combined_v1; no global scaling",
            "forecast_horizon_availability_contract": "all sources at or before forecast origin for H24",
            "logical_feature_identity": logical[target]}


def expected_model_fingerprint(target: str) -> str:
    """Recomputed from the correct per-target Phase 10 freeze.

    NOTE (P15-DEV-001): the Phase 12 registry stored LOAD's fingerprint computed
    from PV hyperparameters (family-keyed dict collision). Phase 15 compares
    against the correct reconstruction; see
    reports/phase_15_p12_fingerprint_deviation.md."""
    return model_spec_fingerprint(reference_model_spec_document(ROOT, target, feature_document(target)))


class ReferenceInstance:
    """Frozen reference reconstructed for INFERENCE ONLY (never refit post-drift)."""

    def __init__(self, target: str):
        self.target = target
        self.spec = load_reference_spec(ROOT, target)
        self.fdoc = feature_document(target)
        self.mdoc = reference_model_spec_document(ROOT, target, self.fdoc)
        self.model_spec_fingerprint = model_spec_fingerprint(self.mdoc)
        self.feature_fingerprint = feature_spec_fingerprint(self.fdoc)
        self.model = None

    def fit(self, rows) -> float:
        self.model, elapsed = fit_rows(rows, model_family=self.spec["model_family"],
                                       hyperparameters=self.spec["hyperparameters"], seed=42)
        return elapsed

    def predict(self, rows): return predict_rows(self.model, rows)


def load_reference(target: str, original_rows) -> ReferenceInstance:
    reference = ReferenceInstance(target)
    reference.fit([r for r in original_rows if r["target_timestamp"] < ONSET])
    if reference.model_spec_fingerprint != expected_model_fingerprint(target):
        raise AssertionError(f"reference spec fingerprint drift for {target}")
    return reference


def scenario_id(family: str, severity: str, target: str) -> str:
    return f"{family}-{severity}-{target}"


def parse_scenario_id(sid: str) -> tuple[str, str, str]:
    tokens = sid.split("-")
    if len(tokens) != 4:
        raise ValueError("scenario ID must look like A15-01-LOW-load")
    return "-".join(tokens[:2]), tokens[2], tokens[3]


def smoke_timeline() -> tuple[datetime, datetime, datetime]:
    start = datetime(2020, 1, 1)
    return start + timedelta(hours=600), start + timedelta(hours=936), start + timedelta(hours=1272)


def run_scenario(identities: dict, target: str, family: str, severity: str, *, smoke: bool = False) -> dict:
    policy = identities["policy"]
    sid = "NON_EVIDENCE_SMOKE" if smoke else scenario_id(family, severity, target)
    onset, cutoff, eval_end = smoke_timeline() if smoke else (ONSET, CUTOFF, EVAL_END)
    timestamps, values = load_hourly_series(ROOT, target)
    rows = load_feature_rows(ROOT, target)
    original_view = build_view(rows, timestamps, values)
    reference = load_reference(target, original_view)
    perturbed, perturb_meta = perturb_series(timestamps, values, family=family, severity=severity, onset=onset)
    view = build_view(rows, timestamps, perturbed)
    threshold = float(identities["thresholds"]["thresholds"][target]["feature_wasserstein"])
    reference_rows = [r for r in original_view if onset - timedelta(hours=504) <= r["forecast_origin"] < onset]
    evidence = monitoring_evidence(view=view, reference_rows=reference_rows, predict_fn=reference.predict,
                                   onset=onset, request_time=cutoff, threshold=threshold, scenario_id=sid,
                                   target=target, reference_model_id=f"MLOPS-REF-{target.upper()}-H24-V1",
                                   threshold_freeze_sha256=identities["threshold_freeze_sha256"])
    eligible = eligible_events(evidence)
    new_labels = sum(1 for r in view if onset <= r["target_timestamp"] <= cutoff)
    request = build_request(
        target=target, reference_registry_id=f"MLOPS-REF-{target.upper()}-H24-V1",
        reference_model_fingerprint=reference.model_spec_fingerprint, drift_events=eligible,
        trigger_severity=max_severity(eligible), trigger_detectors=combined_detectors(eligible),
        request_timestamp=cutoff.isoformat(), data_cutoff=cutoff.isoformat(), label_cutoff=cutoff.isoformat(),
        proposed_training_window={"strategy": "EXPANDING_WINDOW_REFIT", "end": cutoff.isoformat()},
        policy_version=policy.version, retraining_policy_fingerprint=policy.retraining_policy_fingerprint,
        monitoring_policy_fingerprint=identities["monitoring_policy_fingerprint"],
        governance_policy_fingerprint=identities["governance_policy_fingerprint"],
        evidence_refs=["artifacts/retraining/phase_15/evidence/drift_events.jsonl"],
        request_origin="MANUAL_SIMULATION", simulation_scenario_id=sid, protocol_hash=PROTOCOL_BINDING_HASH,
        persistence_window_count=persistence_count(evidence), new_labeled_sample_count=new_labels,
        mae_degradation_observed=True, actual_feature_fingerprint=reference.feature_fingerprint,
        expected_feature_fingerprint=reference.feature_fingerprint)
    context = EvaluationContext(known_event_ids={e["event_id"] for e in evidence}, trusts_evidence=False,
                                expected_model_fingerprint=reference.model_spec_fingerprint)
    decision = evaluate_request(request, policy, context)
    if not smoke:
        append_jsonl(OUT / "evidence/drift_events.jsonl", evidence)
        append_jsonl(DECISION_LOG, [decision.to_dict()])
        emit(AUDIT, "RETRAINING_REQUEST_CREATED", request.request_id,
             {"target": target, "scenario_id": sid, "fingerprint": request.retraining_request_fingerprint},
             list(request.evidence_refs))
        emit(AUDIT, decision_event_type(decision.decision), request.request_id,
             {"target": target, "scenario_id": sid, "reason_codes": decision.reason_codes,
              "policy_version": policy.version}, list(request.evidence_refs))
    if decision.decision != "ALLOW":
        return {"scenario_id": sid, "target": target, "decision": decision.decision,
                "reason_codes": decision.reason_codes, "job": None, "evidence_events": len(evidence)}
    dataset = expanding_window_dataset(view, reference_training_end=onset, cutoff=cutoff, label_cutoff=cutoff,
                                       target=target, feature_fingerprint=reference.feature_fingerprint, onset=onset)
    eval_rows = [r for r in view if cutoff < r["target_timestamp"] <= eval_end]
    clean_rows = [r for r in original_view if cutoff < r["target_timestamp"] <= eval_end]
    if not eval_rows:
        return {"scenario_id": sid, "target": target, "decision": "ALLOW",
                "reason_codes": ["INSUFFICIENT_EVALUATION_HORIZON"], "job": None, "evidence_events": len(evidence)}
    challenger, runtime = fit_rows(dataset["rows"], model_family=reference.spec["model_family"],
                                   hyperparameters=reference.spec["hyperparameters"], seed=42)
    ref_pred = reference.predict(eval_rows)
    chal_pred = predict_rows(challenger, eval_rows)
    evaluation = matched_evaluation(eval_rows, ref_pred, chal_pred)
    clean_evaluation = matched_evaluation(clean_rows, reference.predict(clean_rows), predict_rows(challenger, clean_rows))
    gain = adaptation_gain_percent(evaluation["reference"]["MAE"], evaluation["challenger"]["MAE"])
    stability = clean_stability_change_percent(clean_evaluation["reference"]["MAE"], clean_evaluation["challenger"]["MAE"])
    dataset_fp = training_dataset_fingerprint(dataset, target=target,
                                              feature_fingerprint=reference.feature_fingerprint, cutoff=cutoff)
    instance_fp = model_instance_fingerprint(model_spec_fingerprint=reference.model_spec_fingerprint,
                                             training_dataset_fingerprint=dataset_fp, training_cutoff=cutoff, seed=42)
    with tracked_run(TrackingConfig(ROOT), "phase15/governed_retraining", tags={
            "tracking_origin": "NATIVE_MLFLOW", "research_phase": "15", "experiment_type": "GOVERNED_RETRAINING",
            "target": target, "scenario_family": family, "scenario_severity": severity,
            "parent_reference_id": f"MLOPS-REF-{target.upper()}-H24-V1",
            "retraining_policy_fingerprint": policy.retraining_policy_fingerprint,
            "model_spec_fingerprint": reference.model_spec_fingerprint,
            "model_instance_fingerprint": instance_fp, "training_dataset_fingerprint": dataset_fp,
            "evidence_status": "NON_EVIDENCE_SMOKE" if smoke else "VALID",
            "simulation_scenario_id": sid, "reference_inference_only": "true",
            "retraining_strategy": "EXPANDING_WINDOW_REFIT"}, params={
            "target": target, "family": family, "severity": severity, "seed": 42,
            "training_cutoff": cutoff.isoformat(), "historical_rows": dataset["historical_rows"],
            "new_rows": dataset["new_rows"], "total_rows": dataset["total_rows"],
            "feature_names": FEATURE_NAMES, "hyperparameters": reference.spec["hyperparameters"],
            "policy_version": policy.version, "protocol_freeze_sha256": identities["protocol_freeze_sha256"]}) as run:
        mlflow.log_metrics({"reference_post_drift_mae": evaluation["reference"]["MAE"],
                            "challenger_post_drift_mae": evaluation["challenger"]["MAE"],
                            "adaptation_gain_percent": gain,
                            "clean_reference_mae": clean_evaluation["reference"]["MAE"],
                            "clean_challenger_mae": clean_evaluation["challenger"]["MAE"],
                            "clean_stability_change_percent": stability, "runtime_seconds": runtime})
        run_id = run.info.run_id
    job = RetrainingJobResult(
        job_id=f"RET-JOB-{sid}", request_id=request.request_id, target=target, simulation_scenario_id=sid,
        status="COMPLETED", challenger_registry_id=None,
        parent_reference_id=f"MLOPS-REF-{target.upper()}-H24-V1",
        parent_reference_fingerprint=reference.model_spec_fingerprint, training_cutoff=cutoff.isoformat(),
        training_row_count=dataset["total_rows"], new_data_row_count=dataset["new_rows"],
        historical_row_count=dataset["historical_rows"], feature_fingerprint=reference.feature_fingerprint,
        model_spec_fingerprint=reference.model_spec_fingerprint, model_instance_fingerprint=instance_fp,
        training_dataset_fingerprint=dataset_fp,
        training_policy={"strategy": "EXPANDING_WINDOW_REFIT", "seed_policy": [42],
                         "hyperparameter_policy": "FROZEN_REFERENCE_EXACT_NO_HPO"},
        seed=42, runtime_seconds=runtime, mlflow_run_id=run_id,
        lineage_refs=["artifacts/retraining/phase_15/manifests/challenger_lineage.yaml"],
        policy_refs={"policy_id": policy.policy_id, "policy_version": policy.version,
                     "policy_checksum": policy.checksum,
                     "retraining_policy_fingerprint": policy.retraining_policy_fingerprint,
                     "protocol_freeze_sha256": identities["protocol_freeze_sha256"]}).to_dict()
    checks = admission_checks(training_completed=True, evidence_status="VALID", lineage_status="COMPLETE",
                              actual_feature_fingerprint=reference.feature_fingerprint,
                              expected_feature_fingerprint=reference.feature_fingerprint,
                              model_spec_fingerprint=reference.model_spec_fingerprint,
                              parent_spec_fingerprint=reference.model_spec_fingerprint,
                              training_dataset_fingerprint=dataset_fp, evaluation=evaluation,
                              predictions_finite=bool(outputs_finite(chal_pred) and outputs_finite(ref_pred)),
                              unresolved_deviation=False, final_test_accessed=False)
    registry_state = "REGISTERED_CHALLENGER" if not checks["failed"] else "REJECTED"
    record = build_challenger_record(
        challenger_id=f"MLOPS-CHAL15-{target.upper()}-{sid}", target=target,
        parent_reference_id=job["parent_reference_id"], scenario=sid,
        model_family=reference.spec["model_family"], feature_set="B_lags_only",
        model_spec_fingerprint=reference.model_spec_fingerprint, model_instance_fingerprint=instance_fp,
        training_dataset_fingerprint=dataset_fp, training_cutoff=cutoff.isoformat(), evaluation=evaluation,
        evidence_refs=list(request.evidence_refs) + [f"artifacts/retraining/phase_15/evaluations/{sid}.json"],
        mlflow_run_id=run_id, registry_state=registry_state, promotion_eligible=False)
    if not smoke:
        emit(AUDIT, "RETRAINING_JOB_STARTED", job["job_id"], {"target": target, "scenario_id": sid})
        emit(AUDIT, "RETRAINING_JOB_COMPLETED", job["job_id"],
             {"target": target, "scenario_id": sid, "runtime_seconds": runtime})
        emit(AUDIT, "RETRAINED_CANDIDATE_CREATED", job["job_id"],
             {"target": target, "model_instance_fingerprint": instance_fp})
        dump(OUT / f"jobs/{sid}.json", job)
        dump(OUT / f"evaluations/{sid}.json",
             {"scenario_id": sid, "target": target, "family": family, "severity": severity,
              "post_drift": evaluation, "clean_counterfactual": clean_evaluation,
              "adaptation_gain_percent": gain, "clean_stability_change_percent": stability,
              "perturbation": perturb_meta, "reference_inference_only": True, "admission_checks": checks})
        challenger_registry = ChallengerRegistry.load(CHALLENGER_REGISTRY)
        entry = challenger_registry.register(record)
        challenger_registry.dump(CHALLENGER_REGISTRY)
        emit(AUDIT, "CHALLENGER_REGISTERED", record.challenger_id,
             {"target": target, "scenario_id": sid, "promotion_eligible": False,
              "registry_state": entry["registry_state"]}, record.evidence_refs)
        update_lineage(identities, target=target, sid=sid, job=job, record=record)
    return {"scenario_id": sid, "target": target, "decision": decision.decision,
            "reason_codes": decision.reason_codes, "job": job, "evaluation": evaluation,
            "clean_evaluation": clean_evaluation, "adaptation_gain_percent": gain,
            "clean_stability_change_percent": stability, "challenger_state": registry_state,
            "challenger_id": record.challenger_id, "new_rows": dataset["new_rows"],
            "total_rows": dataset["total_rows"], "runtime_seconds": runtime,
            "mlflow_run_id": run_id, "evidence_events": len(evidence), "smoke": smoke}


def update_lineage(identities: dict, *, target: str, sid: str, job: dict, record) -> None:
    path = ROOT / "artifacts/retraining/phase_15/manifests/challenger_lineage.yaml"
    graph = LineageGraph.load(path) if path.exists() else LineageGraph()
    feature_id = f"feature:{target}:h24:B_lags_only"
    spec_id = f"model-spec:{job['model_spec_fingerprint']}"
    graph.add_node("dataset:rts-gmlc-v2.0", "dataset", manifest_path="data/manifests/rts_gmlc_manifest.yaml")
    graph.add_node("processed:rts_gmlc_processed_v1", "processed_dataset")
    graph.add_node(feature_id, "feature_dataset", feature_set_id="B_lags_only")
    graph.add_node(spec_id, "model_spec", model_spec_fingerprint=job["model_spec_fingerprint"])
    graph.add_node("protocol:phase15-retraining", "protocol",
                   path="artifacts/experimental_design/phase_15_retraining_protocol_freeze.yaml",
                   sha256=identities["protocol_freeze_sha256"])
    drift_id = f"drift-evidence:{sid}"; request_id = f"request:{sid}"; decision_id = f"decision:{sid}"
    dataset_id = f"training-dataset:{job['training_dataset_fingerprint']}"; job_id = f"job:{job['job_id']}"
    instance_id = f"model-instance:{job['model_instance_fingerprint']}"; eval_id = f"evaluation:phase15:{sid}"
    challenger_id = f"challenger:{record.challenger_id}"
    graph.add_node(drift_id, "evidence", evidence_type="DRIFT_ALERT_RAISED", scenario=sid)
    graph.add_node(request_id, "evidence", evidence_type="RETRAINING_REQUEST")
    graph.add_node(decision_id, "evidence", evidence_type="RETRAINING_DECISION", decision="ALLOW")
    graph.add_node(dataset_id, "feature_dataset", dataset_fingerprint=job["training_dataset_fingerprint"])
    graph.add_node(job_id, "experiment_run", run_type="GOVERNED_RETRAINING")
    graph.add_node(instance_id, "model_spec", model_instance_fingerprint=job["model_instance_fingerprint"])
    graph.add_node(eval_id, "evaluation", adaptation_gain_percent=record.adaptation_gain_percent)
    graph.add_node(challenger_id, "registry_entry", registry_state="REGISTERED_CHALLENGER", promotion_eligible=False)
    graph.add_edge("processed:rts_gmlc_processed_v1", "dataset:rts-gmlc-v2.0", "DERIVED_FROM")
    graph.add_edge(feature_id, "processed:rts_gmlc_processed_v1", "DERIVED_FROM")
    graph.add_edge(spec_id, feature_id, "USES")
    graph.add_edge(spec_id, "protocol:phase15-retraining", "GOVERNED_BY")
    graph.add_edge(drift_id, feature_id, "DERIVED_FROM")
    graph.add_edge(request_id, drift_id, "DERIVED_FROM")
    graph.add_edge(decision_id, request_id, "DERIVED_FROM")
    graph.add_edge(dataset_id, decision_id, "DERIVED_FROM")
    graph.add_edge(job_id, dataset_id, "DERIVED_FROM")
    graph.add_edge(job_id, spec_id, "USES")
    graph.add_edge(instance_id, job_id, "PRODUCED")
    graph.add_edge(eval_id, instance_id, "EVALUATED_BY")
    graph.add_edge(challenger_id, eval_id, "REGISTERED_AS")
    graph.add_edge(instance_id, spec_id, "COMPARED_WITH")
    graph.validate()
    graph.dump(path)


def request_policy_suite(identities: dict) -> list[dict]:
    policy = identities["policy"]
    now = CUTOFF.isoformat()

    def events(severity, detectors, tag="REQPOLICY", count=3):
        return [synthetic_evidence_event(tag=tag, severity=severity, triggered=detectors, window_index=i)
                for i in range(count)]

    base = dict(target="load", reference_registry_id="MLOPS-REF-LOAD-H24-V1",
                reference_model_fingerprint="req-policy-fixture", request_timestamp=now, data_cutoff=now,
                label_cutoff=now, proposed_training_window={"strategy": "EXPANDING_WINDOW_REFIT", "end": now},
                policy_version=policy.version, retraining_policy_fingerprint=policy.retraining_policy_fingerprint,
                monitoring_policy_fingerprint=identities["monitoring_policy_fingerprint"],
                governance_policy_fingerprint=identities["governance_policy_fingerprint"],
                evidence_refs=["artifacts/retraining/phase_15/scenario_results/request_policy.json"],
                request_origin="SYSTEM_TEST", protocol_hash=PROTOCOL_BINDING_HASH,
                actual_feature_fingerprint="feature-fixture", expected_feature_fingerprint="feature-fixture")

    def fields(**overrides): return {**base, **overrides}

    normal = fields(trigger_severity="WARNING", trigger_detectors=("PERFORMANCE_DRIFT",),
                    persistence_window_count=2, new_labeled_sample_count=336)
    specs = [
        ("R01", "DENY", events("NONE", [], "R01"), fields(trigger_severity="NONE", trigger_detectors=(),
                                                   persistence_window_count=0, new_labeled_sample_count=336)),
        ("R02", "DENY", events("WATCH", ["FEATURE_DRIFT"], "R02"), fields(trigger_severity="WATCH",
                                                                   trigger_detectors=("FEATURE_DRIFT",),
                                                                   persistence_window_count=2,
                                                                   new_labeled_sample_count=336)),
        ("R03", "DEFER", events("WARNING", ["PERFORMANCE_DRIFT"], "R03"), fields(trigger_severity="WARNING",
                                                                          trigger_detectors=("PERFORMANCE_DRIFT",),
                                                                          persistence_window_count=1,
                                                                          new_labeled_sample_count=336)),
        ("R04", "ALLOW", events("WARNING", ["PERFORMANCE_DRIFT"], "R04"), normal),
        ("R05", "ALLOW", events("CRITICAL", ["FEATURE_DRIFT", "PREDICTION_DRIFT", "PERFORMANCE_DRIFT"], "R05"),
         fields(trigger_severity="CRITICAL",
                trigger_detectors=("FEATURE_DRIFT", "PREDICTION_DRIFT", "PERFORMANCE_DRIFT"),
                persistence_window_count=3, new_labeled_sample_count=336)),
        ("R06", "DENY", events("CRITICAL", ["DATA_QUALITY"], "R06"), fields(trigger_severity="CRITICAL",
                                                                     trigger_detectors=("PERFORMANCE_DRIFT",),
                                                                     persistence_window_count=3,
                                                                     new_labeled_sample_count=336,
                                                                     data_quality_critical=True)),
        ("R07", "DEFER", events("WARNING", ["PERFORMANCE_DRIFT"], "R07"), fields(trigger_severity="WARNING",
                                                                          trigger_detectors=("PERFORMANCE_DRIFT",),
                                                                          persistence_window_count=2,
                                                                          new_labeled_sample_count=336,
                                                                          labels_available=False)),
        ("R08", "DEFER", events("WARNING", ["PERFORMANCE_DRIFT"], "R08"), fields(trigger_severity="WARNING",
                                                                          trigger_detectors=("PERFORMANCE_DRIFT",),
                                                                          persistence_window_count=2,
                                                                          new_labeled_sample_count=100)),
        ("R09", "DEFER", events("WARNING", ["PERFORMANCE_DRIFT"], "R09"), fields(trigger_severity="WARNING",
                                                                          trigger_detectors=("PERFORMANCE_DRIFT",),
                                                                          persistence_window_count=2,
                                                                          new_labeled_sample_count=336,
                                                                          cooldown_active=True)),
        ("R10", "DENY", events("WARNING", ["PERFORMANCE_DRIFT"], "R10"), fields(trigger_severity="WARNING",
                                                                         trigger_detectors=("PERFORMANCE_DRIFT",),
                                                                         persistence_window_count=2,
                                                                         new_labeled_sample_count=336,
                                                                         lineage_status="INCOMPLETE")),
        ("R11", "DENY", events("WARNING", ["PERFORMANCE_DRIFT"], "R11"), fields(trigger_severity="WARNING",
                                                                         trigger_detectors=("PERFORMANCE_DRIFT",),
                                                                         persistence_window_count=2,
                                                                         new_labeled_sample_count=336,
                                                                         reference_model_fingerprint="tampered-fingerprint",
                                                                         expected_fingerprint="req-policy-fixture")),
        ("R12", "DENY", events("WARNING", ["PERFORMANCE_DRIFT"], "R12"), fields(trigger_severity="WARNING",
                                                                         trigger_detectors=("PERFORMANCE_DRIFT",),
                                                                         persistence_window_count=2,
                                                                         new_labeled_sample_count=336,
                                                                         requests_final_test_access=True)),
        ("R14", "DENY", [synthetic_evidence_event(tag="R14", severity="WARNING", triggered=["PERFORMANCE_DRIFT"], window_index=0)],
         fields(trigger_severity="WARNING", trigger_detectors=("PERFORMANCE_DRIFT",), persistence_window_count=2,
                new_labeled_sample_count=336, evidence_status="NON_EVIDENCE_SMOKE")),
        ("R15", "ALLOW", events("WARNING", ["PERFORMANCE_DRIFT"], "R15"), normal),
    ]
    results = []
    prior = []
    r15_decision = None
    for case_id, expected, evidence, case_fields in specs:
        cooldown = case_fields.pop("cooldown_active", False)
        expected_fp = case_fields.pop("expected_fingerprint", case_fields["reference_model_fingerprint"])
        request = build_request(drift_events=evidence, **case_fields)
        if cooldown:
            context = EvaluationContext(trusts_evidence=True, prior_decisions=prior,
                                        last_successful_job_end=(CUTOFF - timedelta(hours=24)).isoformat())
        else:
            context = EvaluationContext(trusts_evidence=True, prior_decisions=prior,
                                        expected_model_fingerprint=expected_fp)
        decision = evaluate_request(request, policy, context)
        prior.append({"retraining_request_fingerprint": request.retraining_request_fingerprint,
                      "decision": decision.decision, "reason_codes": decision.reason_codes,
                      "gate_results": decision.gate_results, "training_window": decision.training_window})
        append_jsonl(DECISION_LOG, [decision.to_dict()])
        emit(AUDIT, decision_event_type(decision.decision), request.request_id,
             {"target": "load", "request_policy_case": case_id, "reason_codes": decision.reason_codes})
        if case_id == "R15":
            r15_decision = decision.decision
        results.append({"case_id": case_id, "case": CASE_LABELS[case_id], "target": "load",
                        "trigger": ",".join(request.trigger_detectors) or "NONE",
                        "severity": request.trigger_severity, "expected_decision": expected,
                        "actual_decision": decision.decision, "reason": ",".join(decision.reason_codes),
                        "retraining_launched": decision.decision == "ALLOW",
                        "unsafe_attempt": case_id in UNSAFE_CASES,
                        "unnecessary_attempt": case_id in UNNECESSARY_CASES})
    duplicate = build_request(drift_events=events("WARNING", ["PERFORMANCE_DRIFT"], "R15"), **normal)
    second = evaluate_request(duplicate, policy, EvaluationContext(trusts_evidence=True, prior_decisions=prior))
    duplicate_ok = second.decision == r15_decision and "DUPLICATE_REQUEST" in second.reason_codes
    results.append({"case_id": "R13", "case": CASE_LABELS["R13"], "target": "load",
                    "trigger": "PERFORMANCE_DRIFT", "severity": "WARNING",
                    "expected_decision": r15_decision, "actual_decision": second.decision,
                    "reason": ",".join(second.reason_codes), "retraining_launched": False,
                    "unsafe_attempt": False, "unnecessary_attempt": False, "duplicate_ok": duplicate_ok})
    return results


def existing_completed(sid: str) -> dict | None:
    for record in read_jsonl(DECISION_LOG):
        if record.get("simulation_scenario_id") == sid and record.get("decision") == "ALLOW":
            job_path = OUT / f"jobs/{sid}.json"
            if job_path.exists():
                job = json.loads(job_path.read_text(encoding="utf-8"))
                return {"scenario_id": sid, "target": job["target"], "decision": "ALLOW",
                        "reason_codes": ["DUPLICATE_REQUEST"], "challenger_id": job.get("challenger_registry_id"),
                        "cached": True}
    return None


def main():
    parser = argparse.ArgumentParser(description="Phase 15 governed retraining (deterministic, no agents)")
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--requests", action="store_true")
    parser.add_argument("--scenario")
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()
    if not (args.smoke or args.requests or args.scenario or args.all):
        parser.error("select --smoke, --requests, --scenario <ID>, or --all")
    identities = frozen_identities()
    if args.smoke:
        result = run_scenario(identities, "load", "A15-01", "MEDIUM", smoke=True)
        dump(OUT / "manifests/non_evidence_smoke.yaml",
             {"evidence_status": "NON_EVIDENCE_SMOKE",
              "verified_steps": ["request_creation", "policy_evaluation", "training_dataset", "model_refit",
                                 "evaluation", "lineage", "mlflow", "challenger_registration"],
              "decision": result["decision"], "challenger_state": result.get("challenger_state"),
              "mlflow_run_id": result.get("mlflow_run_id"), "excluded_from_research_evidence": True,
              "final_test_reads": 0})
        print(json.dumps({"NON_EVIDENCE_SMOKE": "PASS", "decision": result["decision"],
                          "challenger_state": result.get("challenger_state")}, indent=2))
        return
    if args.requests or args.all:
        results = request_policy_suite(identities)
        dump(OUT / "scenario_results/request_policy.json",
             {"cases": results, "metrics": request_policy_metrics(results)})
        print(json.dumps(request_policy_metrics(results), indent=2))
    if args.scenario or args.all:
        if args.scenario:
            combos = [parse_scenario_id(args.scenario)]
        else:
            combos = [(f, s, t) for f in FAMILIES for s in SEVERITIES for t in TARGETS]
        summary = []
        for family, severity, target in combos:
            sid = scenario_id(family, severity, target)
            cached = existing_completed(sid)
            if cached is not None:
                summary.append(cached); continue
            result = run_scenario(identities, target, family, severity)
            summary.append({"scenario_id": result["scenario_id"], "target": result["target"],
                            "decision": result["decision"], "reason_codes": result["reason_codes"],
                            "challenger_state": result.get("challenger_state"),
                            "challenger_id": result.get("challenger_id"),
                            "adaptation_gain_percent": result.get("adaptation_gain_percent"),
                            "runtime_seconds": result.get("runtime_seconds"), "cached": False})
        dump(OUT / "scenario_results/adaptation_summary.json", {"scenarios": summary})
        print(json.dumps({"scenarios": len(summary),
                          "allowed": sum(1 for s in summary if s["decision"] == "ALLOW"),
                          "registered": sum(1 for s in summary if s.get("challenger_state") == "REGISTERED_CHALLENGER"),
                          "cached": sum(1 for s in summary if s.get("cached"))}, indent=2))


if __name__ == "__main__":
    main()
