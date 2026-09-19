from __future__ import annotations
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

LIFECYCLE_STATES = {"EXPERIMENTAL","VALIDATED","REGISTERED_REFERENCE","REGISTERED_CHALLENGER","CHALLENGER_ELIGIBLE","PROMOTION_ELIGIBLE","APPROVAL_PENDING","APPROVED_FOR_CANARY","CANARY_ACTIVE","ACTIVE","ROLLBACK_REQUIRED","ARCHIVED","INVALIDATED"}
APPROVAL_STATES = {"NOT_REQUIRED","REQUIRED","PENDING","APPROVED","REJECTED"}
DECISIONS = {"ALLOW","DENY","REQUIRE_APPROVAL","NO_OP"}
REASON_CODES = {"EVIDENCE_INVALID","LINEAGE_INCOMPLETE","MODEL_SPEC_FINGERPRINT_MISMATCH","FEATURE_SPEC_FINGERPRINT_MISMATCH","PROTOCOL_MISMATCH","REPRODUCIBILITY_INCOMPLETE","UNRESOLVED_DEVIATION","BENCHMARK_GATE_FAILED","STATISTICAL_EVIDENCE_FAILED","APPROVAL_REQUIRED","APPROVAL_REJECTED","INVALID_STATE_TRANSITION","FINAL_TEST_POLICY_VIOLATION","POLICY_VERSION_MISMATCH","ALL_REQUIRED_GATES_PASSED","SIMULATION_APPROVAL_ACCEPTED"}

@dataclass(frozen=True)
class CandidateContext:
    subject_id: str
    evidence_status: str = "VALID"
    official_candidate: bool = True
    lineage_status: str = "COMPLETE"
    actual_model_fingerprint: str = "model-ok"
    expected_model_fingerprint: str = "model-ok"
    actual_feature_fingerprint: str = "feature-ok"
    expected_feature_fingerprint: str = "feature-ok"
    protocol_hash: str = ""
    reproducibility_metadata: str = "COMPLETE"
    deviation_status: str = "NONE"
    benchmark_gate: str = "BENCHMARK_GATE_PASS"
    statistical_evidence: str = "REQUIRED_PASS"
    approval_state: str = "NOT_REQUIRED"
    approval_actor: str | None = None
    policy_mode: str = "RESEARCH"
    requests_final_test_access: bool = False
    requests_integrity_audit_activation: bool = False
    evidence_refs: tuple[str, ...] = ()

@dataclass(frozen=True)
class TransitionRequest:
    subject_id: str
    current_state: str
    proposed_state: str
    actor_type: str = "SYSTEM"
    simulation: bool = False
    claimed_policy_id: str | None = None
    claimed_policy_version: str | None = None
    claimed_policy_checksum: str | None = None

    @property
    def requested_transition(self): return f"{self.current_state} -> {self.proposed_state}"

@dataclass(frozen=True)
class GateResult:
    gate: str
    passed: bool
    reason_code: str | None
    explanation: str

    def to_dict(self): return asdict(self)

@dataclass
class GovernanceDecision:
    subject_id: str
    requested_transition: str
    decision: str
    current_state: str
    proposed_state: str
    policy_id: str
    policy_version: str
    policy_checksum: str
    governance_policy_fingerprint: str
    gate_results: list[dict[str, Any]]
    failed_gates: list[str]
    reason_codes: list[str]
    explanation: str
    evidence_refs: list[str]
    actor_type: str
    simulation: bool
    decision_content_fingerprint: str
    decision_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self): return asdict(self)
    def scientific_content(self):
        value=self.to_dict();value.pop("decision_id",None);value.pop("timestamp",None);return value
