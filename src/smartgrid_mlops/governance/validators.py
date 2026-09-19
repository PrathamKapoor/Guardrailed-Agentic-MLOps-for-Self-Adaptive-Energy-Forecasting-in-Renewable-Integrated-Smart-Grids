from __future__ import annotations
from .schemas import CandidateContext,GateResult,TransitionRequest

def result(gate,passed,reason,ok,fail):return GateResult(gate,passed,None if passed else reason,ok if passed else fail)
def policy_version_gate(c,r,p):
    passed=(r.claimed_policy_id in (None,p.policy_id) and r.claimed_policy_version in (None,p.version) and r.claimed_policy_checksum in (None,p.checksum))
    return result("POLICY_VERSION_GATE",passed,"POLICY_VERSION_MISMATCH","Policy identity matches.","Claimed policy identity does not match the frozen policy.")
def final_test_gate(c,r,p):
    passed=not c.requests_final_test_access and not c.requests_integrity_audit_activation
    return result("FINAL_TEST_POLICY_GATE",passed,"FINAL_TEST_POLICY_VIOLATION","No final-test or integrity-audit access requested.","Phase 13 forbids final-test access and activation of the historical integrity exception.")
def evidence_gate(c,r,p):
    passed=c.evidence_status in p.document["required_evidence_statuses"] and c.official_candidate
    return result("EVIDENCE_VALIDITY_GATE",passed,"EVIDENCE_INVALID","Official evidence is VALID.","Evidence is invalidated, audit-only, or not an official candidate.")
def lineage_gate(c,r,p):return result("LINEAGE_COMPLETENESS_GATE",c.lineage_status==p.document["required_lineage_status"],"LINEAGE_INCOMPLETE","Required lineage is complete.","Required dataset-to-registry lineage is incomplete.")
def model_fingerprint_gate(c,r,p):return result("MODEL_SPEC_FINGERPRINT_GATE",c.actual_model_fingerprint==c.expected_model_fingerprint,"MODEL_SPEC_FINGERPRINT_MISMATCH","Model fingerprint matches the freeze.","Actual model fingerprint differs from the frozen specification.")
def feature_fingerprint_gate(c,r,p):return result("FEATURE_SPEC_FINGERPRINT_GATE",c.actual_feature_fingerprint==c.expected_feature_fingerprint,"FEATURE_SPEC_FINGERPRINT_MISMATCH","Feature fingerprint matches the freeze.","Actual feature fingerprint differs from the frozen specification.")
def protocol_gate(c,r,p):return result("PROTOCOL_COMPATIBILITY_GATE",c.protocol_hash in p.document["accepted_protocol_hashes"],"PROTOCOL_MISMATCH","Protocol hash is recognized.","Protocol hash is not accepted by the frozen policy.")
def reproducibility_gate(c,r,p):return result("REPRODUCIBILITY_METADATA_GATE",c.reproducibility_metadata==p.document["required_reproducibility_metadata"],"REPRODUCIBILITY_INCOMPLETE","Reproducibility metadata is complete.","Required reproducibility metadata is incomplete.")
def deviation_gate(c,r,p):return result("DEVIATION_STATUS_GATE",c.deviation_status!="UNRESOLVED_CRITICAL","UNRESOLVED_DEVIATION","No unresolved critical deviation affects eligibility.","An unresolved critical deviation blocks lifecycle elevation.")
def benchmark_gate(c,r,p):
    required=r.proposed_state in {"PROMOTION_ELIGIBLE","APPROVAL_PENDING","APPROVED_FOR_CANARY","CANARY_ACTIVE","ACTIVE"}
    passed=not required or c.benchmark_gate=="BENCHMARK_GATE_PASS"
    return result("BENCHMARK_GATE",passed,"BENCHMARK_GATE_FAILED","Development benchmark requirement is satisfied or not applicable.","Candidate does not strictly outperform the predefined strongest development benchmark.")
def statistical_gate(c,r,p):
    required=r.proposed_state in {"PROMOTION_ELIGIBLE","APPROVAL_PENDING","APPROVED_FOR_CANARY","CANARY_ACTIVE","ACTIVE"}
    passed=not required or c.statistical_evidence in p.document["statistical_evidence_policy"]["accepted_statuses"]
    return result("STATISTICAL_EVIDENCE_GATE",passed,"STATISTICAL_EVIDENCE_FAILED","Statistical evidence policy is satisfied.","Statistical evidence fails or is insufficient for the requested elevation.")
def state_transition_gate(c,r,p,machine):return result("STATE_TRANSITION_GATE",machine.is_allowed(r.current_state,r.proposed_state),"INVALID_STATE_TRANSITION","Requested transition is defined by policy.","Requested lifecycle transition is not allowed.")
def approval_gate(c,r,p):
    if r.current_state=="PROMOTION_ELIGIBLE" and r.proposed_state=="APPROVAL_PENDING":return GateResult("APPROVAL_GATE",False,"APPROVAL_REQUIRED","Explicit approval is required before canary eligibility.")
    if r.current_state=="APPROVAL_PENDING" and r.proposed_state=="APPROVED_FOR_CANARY":
        if c.approval_state=="REJECTED":return GateResult("APPROVAL_GATE",False,"APPROVAL_REJECTED","Recorded approval was rejected.")
        passed=c.approval_state=="APPROVED" and c.policy_mode=="SIMULATION" and c.approval_actor==p.document["approval_policy"]["simulation_actor"]
        return result("APPROVAL_GATE",passed,"APPROVAL_REQUIRED","Simulation approval is explicitly recorded and labelled.","No acceptable explicit approval evidence is present.")
    return GateResult("APPROVAL_GATE",True,None,"Approval is not required for this transition.")

ORDERED_GATES=(policy_version_gate,final_test_gate,evidence_gate,lineage_gate,model_fingerprint_gate,feature_fingerprint_gate,protocol_gate,reproducibility_gate,deviation_gate,benchmark_gate,statistical_gate)
