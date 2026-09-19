from __future__ import annotations
import copy,json
from pathlib import Path
from .policy_engine import GovernanceEngine
from .schemas import CandidateContext,TransitionRequest

def _load(path):return json.loads(path.read_text(encoding="utf-8"))

class GovernanceSimulator:
    def __init__(self,root:Path,policy):
        self.root=root;self.policy=policy;self.engine=GovernanceEngine(policy)
        self.registry={x["registry_id"]:x for x in _load(root/"artifacts/model_registry/mlops_research_registry.yaml")["entries"]}
        self.lineage=_load(root/"artifacts/mlops/lineage/lineage_index.yaml")
    def _synthetic(self,subject):
        protocol=self.policy.document["accepted_protocol_hashes"][0]
        return CandidateContext(subject,protocol_hash=protocol,evidence_refs=("artifacts/experimental_design/phase_13_governance_scenarios.yaml",))
    def candidate(self,scenario:dict)->CandidateContext:
        fixture=scenario["fixture"];subject=scenario["subject"]
        if fixture=="CURRENT_REFERENCE":
            entry=self.registry[subject]
            context=CandidateContext(subject,evidence_status=entry["evidence_status"],lineage_status="COMPLETE",actual_model_fingerprint=entry["model_spec_fingerprint"],expected_model_fingerprint=entry["model_spec_fingerprint"],actual_feature_fingerprint=entry["feature_spec_fingerprint"],expected_feature_fingerprint=entry["feature_spec_fingerprint"],protocol_hash=entry["protocol_hash"],reproducibility_metadata="COMPLETE",deviation_status="RESOLVED_SCIENTIFIC_INTEGRITY_PASS" if entry["deviation_references"] else "NONE",benchmark_gate=entry["development_benchmark_gate"],statistical_evidence="REQUIRED_FAIL",evidence_refs=tuple(entry["selection_evidence"]))
        elif fixture=="P9_DEV_001":
            entry=self.registry[subject];context=CandidateContext(subject,evidence_status="INVALIDATED",official_candidate=False,lineage_status="INCOMPLETE",actual_model_fingerprint=entry["model_spec_fingerprint"],expected_model_fingerprint=entry["model_spec_fingerprint"],actual_feature_fingerprint="UNKNOWN",expected_feature_fingerprint="UNKNOWN",protocol_hash=entry["protocol_hash"],reproducibility_metadata="INVALID",deviation_status="RESOLVED_ARTIFACT_INVALID",benchmark_gate="NOT_APPLICABLE",statistical_evidence="INSUFFICIENT_EVIDENCE",evidence_refs=tuple(entry["selection_evidence"]))
        elif fixture=="P9_DEV_002_VALID":
            context=self._synthetic(subject);context=CandidateContext(**{**context.__dict__,"deviation_status":"RESOLVED_SCIENTIFIC_INTEGRITY_PASS","evidence_refs":("artifacts/integrity/phase_09/p9_dev_002/semantic_comparison.json","artifacts/mlops/lineage/lineage_index.yaml")})
        else:context=self._synthetic(subject)
        values={**context.__dict__,**scenario.get("mutation",{})}
        for key in ("target","claimed_policy_version","repeat_count"):values.pop(key,None)
        return CandidateContext(**values)
    def request(self,scenario:dict,candidate:CandidateContext)->TransitionRequest:
        mutation=scenario.get("mutation",{})
        return TransitionRequest(scenario["subject"],scenario["current_state"],scenario["proposed_state"],"SYSTEM",candidate.policy_mode=="SIMULATION",claimed_policy_version=mutation.get("claimed_policy_version"))
    def execute(self,scenario:dict):
        candidate=self.candidate(scenario);request=self.request(scenario,candidate);decision=self.engine.evaluate(candidate,request)
        repeats=[]
        for _ in range(int(scenario.get("mutation",{}).get("repeat_count",1))-1):repeats.append(self.engine.evaluate(candidate,request))
        if repeats and any(x.scientific_content()!=decision.scientific_content() for x in repeats):raise AssertionError("Decision content is not deterministic")
        return decision

def calculate_metrics(results:list[dict])->dict:
    total=len(results);correct=sum(x["correct"] for x in results)
    unsafe=[x for x in results if x["unsafe_attempt"]];blocked=sum(x["actual_decision"]=="DENY" for x in unsafe)
    false_allow=sum(x["expected_decision"]=="DENY" and x["actual_decision"]=="ALLOW" for x in results)
    false_deny=sum(x["expected_decision"]=="ALLOW" and x["actual_decision"]=="DENY" for x in results)
    def attempts(ids):return [x for x in results if x["scenario"] in ids]
    def denied(items):return sum(x["actual_decision"]=="DENY" for x in items)
    invalid=attempts({"G05"});finger=attempts({"G07","G08"});lineage=attempts({"G06"});benchmark=attempts({"G01","G02","G03"})
    return {"total_scenarios":total,"expected_allow":sum(x["expected_decision"]=="ALLOW" for x in results),"expected_deny":sum(x["expected_decision"]=="DENY" for x in results),"expected_require_approval":sum(x["expected_decision"]=="REQUIRE_APPROVAL" for x in results),"actual_matches":correct,"decision_correctness_percent":100*correct/total,"false_allow":false_allow,"false_deny":false_deny,"unsafe_transition_attempts":len(unsafe),"unsafe_transitions_blocked":blocked,"unsafe_transition_prevention_rate_percent":100*blocked/len(unsafe) if unsafe else 100.0,"invalid_evidence_admission_attempts":len(invalid),"invalid_evidence_blocked":denied(invalid),"fingerprint_tampering_attempts":len(finger),"fingerprint_tampering_blocked":denied(finger),"lineage_violations_attempted":len(lineage),"lineage_violations_blocked":denied(lineage),"benchmark_failure_promotion_attempts":len(benchmark),"benchmark_failure_promotion_attempts_blocked":denied(benchmark),"approval_required_decisions":sum(x["actual_decision"]=="REQUIRE_APPROVAL" for x in results),"final_test_policy_violations_blocked":sum(x["scenario"]=="G15" and x["actual_decision"]=="DENY" for x in results),"decision_determinism":"PASS"}
