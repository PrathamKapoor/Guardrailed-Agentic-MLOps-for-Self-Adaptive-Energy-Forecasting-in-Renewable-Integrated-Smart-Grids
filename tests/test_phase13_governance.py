from __future__ import annotations
import json
from pathlib import Path
import pytest
from smartgrid_mlops.governance.policies import GovernancePolicy
from smartgrid_mlops.governance.policy_engine import GovernanceEngine
from smartgrid_mlops.governance.schemas import CandidateContext,TransitionRequest,LIFECYCLE_STATES
from smartgrid_mlops.governance.simulator import GovernanceSimulator
from smartgrid_mlops.governance.state_machine import LifecycleStateMachine

ROOT=Path(__file__).parents[1];POLICY=GovernancePolicy.load(ROOT/"config/governance/phase_13_policy.yaml");ENGINE=GovernanceEngine(POLICY)
def candidate(**kw):
 values={"protocol_hash":POLICY.document["accepted_protocol_hashes"][0],**kw};return CandidateContext("x",**values)
def decide(current="REGISTERED_CHALLENGER",proposed="PROMOTION_ELIGIBLE",c=None,**req):return ENGINE.evaluate(c or candidate(),TransitionRequest((c or candidate()).subject_id,current,proposed,**req))
def scenarios():return json.loads((ROOT/"artifacts/experimental_design/phase_13_governance_scenarios.yaml").read_text())["scenarios"]

def test_all_declared_legal_transitions_and_terminal_states():
 machine=LifecycleStateMachine(POLICY.document["transition_rules"])
 for current,targets in POLICY.document["transition_rules"].items():
  for target in targets:assert machine.is_allowed(current,target)
 assert machine.is_terminal("INVALIDATED") and machine.is_terminal("ARCHIVED")
 assert not machine.legal_transitions("INVALIDATED") and not machine.legal_transitions("ARCHIVED")

@pytest.mark.parametrize("current,proposed",[("INVALIDATED","PROMOTION_ELIGIBLE"),("EXPERIMENTAL","ACTIVE"),("REGISTERED_REFERENCE","ACTIVE"),("APPROVAL_PENDING","ACTIVE"),("ARCHIVED","VALIDATED")])
def test_forbidden_transitions(current,proposed):assert "INVALID_STATE_TRANSITION" in decide(current,proposed).reason_codes

def test_baseline_is_not_a_lifecycle_candidate():
 machine=LifecycleStateMachine(POLICY.document["transition_rules"]);assert not machine.validate_baseline("BASELINE_COMPARATOR","NOT_APPLICABLE_BASELINE","VALIDATED")

@pytest.mark.parametrize("updates,reason",[
 ({"evidence_status":"INVALIDATED"},"EVIDENCE_INVALID"),({"official_candidate":False},"EVIDENCE_INVALID"),({"lineage_status":"INCOMPLETE"},"LINEAGE_INCOMPLETE"),({"actual_model_fingerprint":"bad"},"MODEL_SPEC_FINGERPRINT_MISMATCH"),({"actual_feature_fingerprint":"bad"},"FEATURE_SPEC_FINGERPRINT_MISMATCH"),({"protocol_hash":"bad"},"PROTOCOL_MISMATCH"),({"reproducibility_metadata":"PARTIAL"},"REPRODUCIBILITY_INCOMPLETE"),({"deviation_status":"UNRESOLVED_CRITICAL"},"UNRESOLVED_DEVIATION"),({"benchmark_gate":"BENCHMARK_GATE_FAIL"},"BENCHMARK_GATE_FAILED"),({"statistical_evidence":"REQUIRED_FAIL"},"STATISTICAL_EVIDENCE_FAILED"),({"requests_final_test_access":True},"FINAL_TEST_POLICY_VIOLATION"),({"requests_integrity_audit_activation":True},"FINAL_TEST_POLICY_VIOLATION")])
def test_policy_gate_failures(updates,reason):assert reason in decide(c=candidate(**updates)).reason_codes

def test_valid_all_gates_pass_and_matching_fingerprints():assert decide().decision=="ALLOW"

def test_resolved_deviation_and_p9_dev_002_logical_provenance_pass():
 scenario=next(x for x in scenarios() if x["id"]=="G16");decision=GovernanceSimulator(ROOT,POLICY).execute(scenario)
 assert decision.decision=="ALLOW" and not decision.failed_gates

def test_invalid_p9_dev_001_fails_evidence():
 scenario=next(x for x in scenarios() if x["id"]=="G05");decision=GovernanceSimulator(ROOT,POLICY).execute(scenario)
 assert decision.decision=="DENY" and decision.reason_codes[0]=="EVIDENCE_INVALID"

def test_approval_required_rejected_and_simulation_approved():
 c=candidate(approval_state="PENDING");d=decide("PROMOTION_ELIGIBLE","APPROVAL_PENDING",c);assert d.decision=="REQUIRE_APPROVAL" and d.reason_codes==["APPROVAL_REQUIRED"]
 c=candidate(approval_state="REJECTED");assert decide("APPROVAL_PENDING","APPROVED_FOR_CANARY",c).reason_codes==["APPROVAL_REJECTED"]
 c=candidate(approval_state="APPROVED",policy_mode="SIMULATION",approval_actor="SIMULATION_POLICY");d=decide("APPROVAL_PENDING","APPROVED_FOR_CANARY",c,simulation=True);assert d.decision=="ALLOW" and d.reason_codes==["SIMULATION_APPROVAL_ACCEPTED"]

def test_policy_version_mismatch():assert "POLICY_VERSION_MISMATCH" in decide(claimed_policy_version="wrong").reason_codes

def test_current_reference_initialization_challengers_and_baselines():
 entries=json.loads((ROOT/"artifacts/model_registry/lifecycle_registry.yaml").read_text())["entries"]
 refs=[x for x in entries if x["research_role"]=="REFERENCE"];assert len(refs)==3 and all(x["lifecycle_state"]=="REGISTERED_REFERENCE" and not x["promotion_eligible"] for x in refs)
 assert all(x["lifecycle_state"]=="REGISTERED_CHALLENGER" for x in entries if x["research_role"]=="CHALLENGER")
 assert all(x["lifecycle_state"]=="NOT_APPLICABLE_BASELINE" for x in entries if x["research_role"]=="BASELINE_COMPARATOR")

@pytest.mark.parametrize("scenario_id",["G01","G02","G03"])
def test_current_reference_promotion_blocked_by_benchmark(scenario_id):
 scenario=next(x for x in scenarios() if x["id"]==scenario_id);d=GovernanceSimulator(ROOT,POLICY).execute(scenario)
 assert d.decision=="DENY" and d.reason_codes[0]=="BENCHMARK_GATE_FAILED"

def test_decision_content_is_deterministic():
 first=decide();second=decide();assert first.scientific_content()==second.scientific_content();assert first.decision_id!=second.decision_id

def test_decision_auditability_schema():
 d=decide().to_dict();required={"decision_id","policy_checksum","governance_policy_fingerprint","subject_id","requested_transition","gate_results","reason_codes","evidence_refs","decision_content_fingerprint"};assert required<=d.keys();assert len(d["gate_results"])==13

def test_scenario_freeze_complete_and_no_final_test_data_path():
 ids={x["id"] for x in scenarios()};assert ids=={f"G{i:02d}" for i in range(1,19)}
 source=(ROOT/"scripts/run_governance_simulation.py").read_text();assert "add_argument(\"--final" not in source and "add_argument('--final" not in source

def test_policy_checksum_and_protocol_freeze_integrity():
 assert POLICY.checksum==(ROOT/"config/governance/phase_13_policy.sha256").read_text().strip()
 freeze=json.loads((ROOT/"artifacts/experimental_design/phase_13_governance_protocol_freeze.yaml").read_text());assert freeze["policy_checksum"]==POLICY.checksum and freeze["final_test_non_access_policy"]["phase_13_new_final_test_reads"]==0

def test_genuine_allow_path_with_all_thirteen_gates_passed():
    """Regression test: verifies that a fully compliant challenger passes all 13 gates and achieves an ALLOW decision."""
    ctx = CandidateContext(
        subject_id="ALLOW-CHALLENGER-REGRESSION",
        evidence_status="VALID",
        lineage_status="COMPLETE",
        actual_model_fingerprint="fp:model:valid",
        expected_model_fingerprint="fp:model:valid",
        actual_feature_fingerprint="fp:feat:valid",
        expected_feature_fingerprint="fp:feat:valid",
        protocol_hash=POLICY.document["accepted_protocol_hashes"][0],
        reproducibility_metadata="COMPLETE",
        deviation_status="RESOLVED",
        benchmark_gate="BENCHMARK_GATE_PASS",
        statistical_evidence="REQUIRED_PASS",
        approval_state="APPROVED",
        approval_actor="SIMULATION_POLICY",
        policy_mode="SIMULATION",
        evidence_refs=["artifacts/mlops/evidence/regression.json"],
    )
    req = TransitionRequest(
        subject_id="ALLOW-CHALLENGER-REGRESSION",
        current_state="APPROVAL_PENDING",
        proposed_state="APPROVED_FOR_CANARY",
        actor_type="SIMULATION_POLICY",
        simulation=True,
    )
    decision = ENGINE.evaluate(ctx, req)
    assert decision.decision == "ALLOW"
    assert len(decision.gate_results) == 13
    assert not decision.failed_gates
    assert decision.reason_codes == ["SIMULATION_APPROVAL_ACCEPTED"]
    assert decision.decision_content_fingerprint is not None
    # Verify every gate individually passed
    gate_names = [g["gate"] for g in decision.gate_results]
    assert len(gate_names) == 13
    assert all(g["passed"] is True for g in decision.gate_results)

