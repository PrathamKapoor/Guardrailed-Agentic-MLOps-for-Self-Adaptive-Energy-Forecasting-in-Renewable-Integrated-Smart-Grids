from __future__ import annotations
from uuid import uuid4
from .schemas import RetrainingRequest
from smartgrid_mlops.mlops.fingerprints import fingerprint


def request_fingerprint(*, target: str, reference_registry_id: str, reference_model_fingerprint: str,
                        drift_event_ids, data_cutoff: str, label_cutoff: str,
                        policy_fingerprint: str, scenario_id: str | None) -> str:
    return fingerprint({
        "target": target, "reference_registry_id": reference_registry_id,
        "reference_model_fingerprint": reference_model_fingerprint,
        "triggering_drift_event_ids": sorted(drift_event_ids),
        "data_cutoff_timestamp": data_cutoff, "label_availability_cutoff": label_cutoff,
        "retraining_policy_fingerprint": policy_fingerprint, "simulation_scenario_id": scenario_id,
    }, "retraining-request-v1")


def build_request(*, target: str, reference_registry_id: str, reference_model_fingerprint: str,
                  drift_events, trigger_severity: str, trigger_detectors,
                  request_timestamp: str, data_cutoff: str, label_cutoff: str,
                  proposed_training_window: dict, policy_version: str,
                  retraining_policy_fingerprint: str, monitoring_policy_fingerprint: str,
                  governance_policy_fingerprint: str, evidence_refs, request_origin: str,
                  simulation_scenario_id: str | None = None, protocol_hash: str = "",
                  persistence_window_count: int = 0, new_labeled_sample_count: int = 0,
                  data_quality_critical: bool = False, labels_available: bool = True,
                  reference_state: str = "REGISTERED_REFERENCE", lineage_status: str = "COMPLETE",
                  actual_feature_fingerprint: str = "feature-ok",
                  expected_feature_fingerprint: str = "feature-ok", evidence_status: str = "VALID",
                  requests_final_test_access: bool = False, mae_degradation_observed: bool = True,
                  job_already_running: bool = False, claimed_policy_id: str | None = None,
                  claimed_policy_version: str | None = None,
                  claimed_policy_checksum: str | None = None) -> RetrainingRequest:
    event_ids = tuple(sorted({e["event_id"] for e in drift_events}))
    fp = request_fingerprint(target=target, reference_registry_id=reference_registry_id,
                             reference_model_fingerprint=reference_model_fingerprint,
                             drift_event_ids=event_ids, data_cutoff=data_cutoff, label_cutoff=label_cutoff,
                             policy_fingerprint=retraining_policy_fingerprint, scenario_id=simulation_scenario_id)
    return RetrainingRequest(
        request_id=str(uuid4()), target=target, reference_registry_id=reference_registry_id,
        reference_model_fingerprint=reference_model_fingerprint, triggering_drift_event_ids=event_ids,
        trigger_severity=trigger_severity, trigger_detectors=tuple(sorted(set(trigger_detectors))),
        request_timestamp=request_timestamp, data_cutoff_timestamp=data_cutoff,
        label_availability_cutoff=label_cutoff, proposed_training_window=dict(proposed_training_window),
        policy_version=policy_version, monitoring_policy_fingerprint=monitoring_policy_fingerprint,
        governance_policy_fingerprint=governance_policy_fingerprint, evidence_refs=tuple(evidence_refs),
        request_origin=request_origin, simulation_scenario_id=simulation_scenario_id,
        claimed_policy_id=claimed_policy_id, claimed_policy_version=claimed_policy_version,
        claimed_policy_checksum=claimed_policy_checksum, protocol_hash=protocol_hash,
        persistence_window_count=persistence_window_count,
        new_labeled_sample_count=new_labeled_sample_count, data_quality_critical=data_quality_critical,
        labels_available=labels_available, reference_state=reference_state,
        lineage_status=lineage_status, actual_feature_fingerprint=actual_feature_fingerprint,
        expected_feature_fingerprint=expected_feature_fingerprint, evidence_status=evidence_status,
        requests_final_test_access=requests_final_test_access,
        mae_degradation_observed=mae_degradation_observed, job_already_running=job_already_running,
        retraining_request_fingerprint=fp,
    )


def find_existing_decision(decision_records: list[dict], request_fingerprint: str) -> dict | None:
    for record in decision_records:
        if record.get("retraining_request_fingerprint") == request_fingerprint:
            return record
    return None
