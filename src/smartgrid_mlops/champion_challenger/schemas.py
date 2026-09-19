from __future__ import annotations
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

DECISIONS = {"APPROVE", "REJECT", "DEFER"}
ROLLBACK_OUTCOMES = {"ROLLBACK_COMPLETED", "ROLLBACK_BLOCKED"}

GATE_ORDER = (
    "POLICY_VERSION_GATE", "FINAL_TEST_GATE", "REGISTRATION_GATE", "LINEAGE_GATE",
    "MODEL_FINGERPRINT_GATE", "FEATURE_FINGERPRINT_GATE", "PROTOCOL_GATE", "METADATA_GATE",
    "EVALUATION_GATE", "PERFORMANCE_GATE", "BENCHMARK_GATE", "STATISTICAL_GATE", "APPROVAL_GATE",
)

REASON_CODES = {
    "POLICY_VERSION_MISMATCH", "FINAL_TEST_POLICY_VIOLATION", "CHALLENGER_NOT_REGISTERED",
    "LINEAGE_INCOMPLETE", "MODEL_FINGERPRINT_MISMATCH", "FEATURE_FINGERPRINT_MISMATCH",
    "PROTOCOL_MISMATCH", "METADATA_INCOMPLETE", "EVALUATION_INCOMPLETE", "CHALLENGER_NOT_BETTER",
    "BENCHMARK_REQUIREMENT_NOT_SATISFIED", "STATISTICAL_EVIDENCE_INSUFFICIENT",
    "APPROVAL_REJECTED", "APPROVAL_REQUIRED", "PROMOTION_APPROVED",
    "CANARY_FAILED", "CANARY_PASSED", "MODEL_PROMOTED",
    "POST_PROMOTION_DEGRADATION", "NO_DEGRADATION",
    "ROLLBACK_VERIFICATION_FAILED", "ROLLBACK_COMPLETED", "ROLLBACK_BLOCKED",
}

AUDIT_EVENT_TYPES = (
    "CHALLENGER_EVALUATED", "PROMOTION_REQUESTED", "PROMOTION_APPROVED", "PROMOTION_REJECTED",
    "PROMOTION_DEFERRED", "CANARY_STARTED", "CANARY_FAILED", "MODEL_PROMOTED",
    "ROLLBACK_REQUESTED", "ROLLBACK_COMPLETED", "ROLLBACK_BLOCKED",
)


@dataclass(frozen=True)
class ChallengerEvaluationContext:
    """Everything the deterministic promotion policy is allowed to see."""
    challenger_id: str
    reference_id: str
    target: str
    simulation: bool = True
    registered: bool = True
    lineage_status: str = "COMPLETE"
    actual_model_fingerprint: str = "model-ok"
    expected_model_fingerprint: str = "model-ok"
    actual_feature_fingerprint: str = "feature-ok"
    expected_feature_fingerprint: str = "feature-ok"
    protocol_hash: str = ""
    metadata_complete: bool = True
    evaluation_completed: bool = True
    matched_evaluation_rows: int = 336
    reference_mae: float = 100.0
    challenger_mae: float = 90.0
    benchmark_gate: str = "BENCHMARK_GATE_PASS"
    statistical_evidence: str = "REQUIRED_PASS"
    approval_state: str = "NOT_REQUIRED"
    approval_actor: str | None = None
    policy_mode: str = "SIMULATION"
    requests_final_test_access: bool = False
    evidence_status: str = "VALID"
    claimed_policy_id: str | None = None
    claimed_policy_version: str | None = None
    claimed_policy_checksum: str | None = None
    canary_regression_percent: float = -5.0
    post_promotion_regression_percent: float = 0.0
    evaluation_metrics: dict = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]: return asdict(self)


@dataclass(frozen=True)
class GateOutcome:
    gate: str
    passed: bool
    reason_code: str | None
    explanation: str

    def to_dict(self) -> dict[str, Any]: return asdict(self)


@dataclass
class PromotionDecision:
    decision_id: str
    challenger_id: str
    reference_id: str
    target: str
    decision: str
    reason_codes: list[str]
    gate_results: list[dict]
    metrics: dict
    policy_id: str
    policy_version: str
    policy_checksum: str
    promotion_policy_fingerprint: str
    simulation: bool
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]: return asdict(self)

    def scientific_content(self) -> dict[str, Any]:
        value = self.to_dict(); value.pop("decision_id", None); value.pop("timestamp", None); return value


@dataclass
class CanaryOutcome:
    challenger_id: str
    passed: bool
    canary_regression_percent: float
    max_allowed_regression_percent: float
    reason_code: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]: return asdict(self)


@dataclass
class PreservationRecord:
    model_id: str
    role: str
    artifact_path: str
    model_spec_fingerprint: str
    lineage_node: str
    preserved_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]: return asdict(self)


@dataclass
class RollbackRecord:
    rollback_id: str
    promoted_model_id: str
    previous_model_id: str
    triggered: bool
    degradation_percent: float
    threshold_percent: float
    verification: dict
    outcome: str
    reason_code: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]: return asdict(self)
