from __future__ import annotations

def apply_allowed_transition(record:dict,decision)->dict:
    """Pure state update; callers decide whether a simulation should persist it."""
    if decision.decision!="ALLOW":return dict(record)
    updated=dict(record);updated["lifecycle_state"]=decision.proposed_state;updated["last_policy_decision"]=decision.decision_id
    updated["promotion_eligible"]=decision.proposed_state in {"PROMOTION_ELIGIBLE","APPROVAL_PENDING","APPROVED_FOR_CANARY","CANARY_ACTIVE","ACTIVE"}
    return updated
