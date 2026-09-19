from __future__ import annotations
from smartgrid_mlops.mlops.fingerprints import fingerprint

EXPLANATIONS={
 "EVIDENCE_INVALID":"DENY: Evidence is invalidated or audit-only and cannot support official lifecycle eligibility.",
 "LINEAGE_INCOMPLETE":"DENY: Required dataset-to-registry lineage is incomplete.",
 "MODEL_SPEC_FINGERPRINT_MISMATCH":"DENY: The candidate model specification does not match its frozen fingerprint.",
 "FEATURE_SPEC_FINGERPRINT_MISMATCH":"DENY: The feature specification does not match its frozen fingerprint.",
 "PROTOCOL_MISMATCH":"DENY: The candidate references an unrecognized frozen protocol.",
 "REPRODUCIBILITY_INCOMPLETE":"DENY: Required reproducibility metadata is incomplete.",
 "UNRESOLVED_DEVIATION":"DENY: An unresolved critical deviation blocks lifecycle elevation.",
 "BENCHMARK_GATE_FAILED":"DENY: Candidate is a valid research record but fails the predefined development benchmark gate and is not promotion eligible.",
 "STATISTICAL_EVIDENCE_FAILED":"DENY: Required statistical evidence is failing or insufficient.",
 "APPROVAL_REQUIRED":"REQUIRE_APPROVAL: Explicit approval is required; promotion eligibility does not authorize activation.",
 "APPROVAL_REJECTED":"DENY: Explicit approval evidence records rejection.",
 "INVALID_STATE_TRANSITION":"DENY: The requested lifecycle transition is not defined by the frozen state machine.",
 "FINAL_TEST_POLICY_VIOLATION":"DENY: Phase 13 forbids final-test access and integrity-audit activation.",
 "POLICY_VERSION_MISMATCH":"DENY: The claimed policy identity differs from the frozen policy.",
 "ALL_REQUIRED_GATES_PASSED":"ALLOW: All deterministic gates required for this transition passed.",
 "SIMULATION_APPROVAL_ACCEPTED":"ALLOW: Explicit simulation-only approval was accepted and was not represented as human approval."
}

def decision_fingerprint(content:dict)->str:return fingerprint(content,"governance-decision-v1")
