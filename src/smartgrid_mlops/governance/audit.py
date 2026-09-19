from __future__ import annotations
from pathlib import Path
from smartgrid_mlops.mlops.audit import append_audit_event
from smartgrid_mlops.mlops.schemas import AuditEvent

def audit_decision(path:Path,decision,scenario_id:str):
    append_audit_event(path,AuditEvent("GOVERNANCE_EVALUATED",decision.subject_id,"SYSTEM","13",{"decision_id":decision.decision_id,"scenario_id":scenario_id,"decision":decision.decision,"policy_checksum":decision.policy_checksum},decision.evidence_refs))
    event_type={"ALLOW":"TRANSITION_ALLOWED","DENY":"TRANSITION_DENIED","REQUIRE_APPROVAL":"APPROVAL_REQUIRED","NO_OP":"GOVERNANCE_EVALUATED"}[decision.decision]
    append_audit_event(path,AuditEvent(event_type,decision.subject_id,"SYSTEM","13",{"decision_id":decision.decision_id,"requested_transition":decision.requested_transition,"reason_codes":decision.reason_codes},decision.evidence_refs))
    if decision.decision=="DENY":append_audit_event(path,AuditEvent("POLICY_VIOLATION",decision.subject_id,"SYSTEM","13",{"decision_id":decision.decision_id,"failed_gates":decision.failed_gates},decision.evidence_refs))
