from __future__ import annotations
from .decisions import EXPLANATIONS,decision_fingerprint
from .schemas import CandidateContext,GovernanceDecision,TransitionRequest
from .state_machine import LifecycleStateMachine
from .validators import ORDERED_GATES,approval_gate,state_transition_gate

class GovernanceEngine:
    def __init__(self,policy):self.policy=policy;self.machine=LifecycleStateMachine(policy.document["transition_rules"])
    def evaluate(self,candidate:CandidateContext,request:TransitionRequest)->GovernanceDecision:
        if candidate.subject_id!=request.subject_id:raise ValueError("Subject mismatch")
        gates=[fn(candidate,request,self.policy) for fn in ORDERED_GATES]
        gates.append(state_transition_gate(candidate,request,self.policy,self.machine));gates.append(approval_gate(candidate,request,self.policy))
        failed=[g for g in gates if not g.passed]
        reasons=[g.reason_code for g in failed if g.reason_code]
        if reasons==["APPROVAL_REQUIRED"] and request.current_state=="PROMOTION_ELIGIBLE" and request.proposed_state=="APPROVAL_PENDING":decision="REQUIRE_APPROVAL"
        elif reasons:decision="DENY"
        else:decision="ALLOW"
        primary=("SIMULATION_APPROVAL_ACCEPTED" if decision=="ALLOW" and request.current_state=="APPROVAL_PENDING" else (reasons[0] if reasons else "ALL_REQUIRED_GATES_PASSED"))
        stable={"subject_id":request.subject_id,"requested_transition":request.requested_transition,"decision":decision,"current_state":request.current_state,"proposed_state":request.proposed_state,"policy_fingerprint":self.policy.governance_policy_fingerprint,"gate_results":[g.to_dict() for g in gates],"reason_codes":reasons or [primary],"evidence_refs":list(candidate.evidence_refs),"actor_type":request.actor_type,"simulation":request.simulation}
        fp=decision_fingerprint(stable)
        return GovernanceDecision(request.subject_id,request.requested_transition,decision,request.current_state,request.proposed_state,self.policy.policy_id,self.policy.version,self.policy.checksum,self.policy.governance_policy_fingerprint,[g.to_dict() for g in gates],[g.gate for g in failed],reasons or [primary],EXPLANATIONS[primary],list(candidate.evidence_refs),request.actor_type,request.simulation,fp)
