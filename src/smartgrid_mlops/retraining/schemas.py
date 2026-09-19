from __future__ import annotations
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

DECISIONS = {"ALLOW", "DENY", "DEFER"}
REQUEST_ORIGINS = {"MONITORING_POLICY", "MANUAL_SIMULATION", "SYSTEM_TEST"}

REASON_CODES = {
    "DRIFT_EVIDENCE_INVALID", "DRIFT_SEVERITY_INSUFFICIENT", "DRIFT_NOT_PERSISTENT",
    "PERFORMANCE_EVIDENCE_INSUFFICIENT", "DATA_QUALITY_BLOCK", "LABELS_NOT_AVAILABLE",
    "INSUFFICIENT_NEW_DATA", "RETRAINING_COOLDOWN_ACTIVE", "REFERENCE_STATE_INVALID",
    "LINEAGE_INCOMPLETE", "MODEL_FINGERPRINT_MISMATCH", "FEATURE_FINGERPRINT_MISMATCH",
    "PROTOCOL_MISMATCH", "FINAL_TEST_POLICY_VIOLATION", "RETRAINING_ALREADY_RUNNING",
    "DUPLICATE_REQUEST", "REQUEST_ORIGIN_INVALID", "POLICY_VERSION_MISMATCH",
    "RETRAINING_ALLOWED", "RETRAINING_DEFERRED", "RETRAINING_DENIED",
}

GATE_ORDER = (
    "POLICY_VERSION_GATE", "REQUEST_ORIGIN_GATE", "DRIFT_EVIDENCE_GATE", "DRIFT_SEVERITY_GATE",
    "DRIFT_PERSISTENCE_GATE", "PERFORMANCE_SIGNAL_GATE", "DATA_QUALITY_GATE",
    "LABEL_AVAILABILITY_GATE", "MINIMUM_NEW_DATA_GATE", "COOLDOWN_GATE", "REFERENCE_STATE_GATE",
    "LINEAGE_GATE", "MODEL_FINGERPRINT_GATE", "FEATURE_FINGERPRINT_GATE", "PROTOCOL_GATE",
    "FINAL_TEST_POLICY_GATE", "JOB_CONCURRENCY_GATE",
)


@dataclass(frozen=True)
class RetrainingRequest:
    request_id: str
    target: str
    reference_registry_id: str
    reference_model_fingerprint: str
    triggering_drift_event_ids: tuple[str, ...]
    trigger_severity: str
    trigger_detectors: tuple[str, ...]
    request_timestamp: str
    data_cutoff_timestamp: str
    label_availability_cutoff: str
    proposed_training_window: dict
    policy_version: str
    monitoring_policy_fingerprint: str
    governance_policy_fingerprint: str
    evidence_refs: tuple[str, ...]
    request_origin: str
    simulation_scenario_id: str | None = None
    claimed_policy_id: str | None = None
    claimed_policy_version: str | None = None
    claimed_policy_checksum: str | None = None
    protocol_hash: str = ""
    persistence_window_count: int = 0
    new_labeled_sample_count: int = 0
    data_quality_critical: bool = False
    labels_available: bool = True
    reference_state: str = "REGISTERED_REFERENCE"
    lineage_status: str = "COMPLETE"
    actual_feature_fingerprint: str = "feature-ok"
    expected_feature_fingerprint: str = "feature-ok"
    evidence_status: str = "VALID"
    requests_final_test_access: bool = False
    mae_degradation_observed: bool = True
    job_already_running: bool = False
    retraining_request_fingerprint: str = ""

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["triggering_drift_event_ids"] = list(self.triggering_drift_event_ids)
        value["trigger_detectors"] = list(self.trigger_detectors)
        value["evidence_refs"] = list(self.evidence_refs)
        return value


@dataclass(frozen=True)
class GateOutcome:
    gate: str
    passed: bool
    reason_code: str | None
    explanation: str

    def to_dict(self) -> dict[str, Any]: return asdict(self)


@dataclass
class RetrainingDecision:
    request_id: str
    target: str
    decision: str
    reason_codes: list[str]
    gate_results: list[dict]
    policy_id: str
    policy_version: str
    policy_checksum: str
    retraining_policy_fingerprint: str
    evidence_refs: list[str]
    data_cutoff: str
    label_cutoff: str
    training_window: dict | None
    retraining_request_fingerprint: str
    simulation_scenario_id: str | None
    decision_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]: return asdict(self)

    def scientific_content(self) -> dict[str, Any]:
        value = self.to_dict()
        for volatile in ("decision_id", "timestamp", "request_id"):
            value.pop(volatile, None)
        return value


@dataclass
class RetrainingJobResult:
    job_id: str
    request_id: str
    target: str
    simulation_scenario_id: str | None
    status: str
    challenger_registry_id: str | None
    parent_reference_id: str
    parent_reference_fingerprint: str
    training_cutoff: str
    training_row_count: int
    new_data_row_count: int
    historical_row_count: int
    feature_fingerprint: str
    model_spec_fingerprint: str
    model_instance_fingerprint: str
    training_dataset_fingerprint: str
    training_policy: dict
    seed: int
    runtime_seconds: float
    mlflow_run_id: str | None
    lineage_refs: list[str]
    policy_refs: dict
    failure_reason: str | None = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]: return asdict(self)


@dataclass
class ChallengerRecord:
    challenger_id: str
    target: str
    parent_reference: str
    scenario: str
    model_family: str
    feature_set: str
    model_spec_fingerprint: str
    model_instance_fingerprint: str
    training_dataset_fingerprint: str
    training_cutoff: str
    evaluation_window_start: str
    evaluation_window_end: str
    reference_mae: float | None
    challenger_mae: float | None
    adaptation_gain_percent: float | None
    registry_state: str
    promotion_eligible: bool
    evidence_refs: list[str]
    mlflow_run_id: str | None = None

    def to_dict(self) -> dict[str, Any]: return asdict(self)
