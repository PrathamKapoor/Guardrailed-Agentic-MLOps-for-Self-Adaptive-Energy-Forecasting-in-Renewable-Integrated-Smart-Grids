"""Phase 16 audit events extending the append-oriented audit log."""
from __future__ import annotations
from pathlib import Path
from smartgrid_mlops.mlops.audit import append_audit_event
from smartgrid_mlops.mlops.schemas import AuditEvent
from .schemas import AUDIT_EVENT_TYPES


def emit(path: Path, event_type: str, subject_id: str, details: dict, evidence_refs=None, phase: str = "16") -> None:
    if event_type not in AUDIT_EVENT_TYPES:
        raise ValueError(f"Unknown champion-challenger audit event {event_type}")
    append_audit_event(Path(path), AuditEvent(event_type, subject_id, "SYSTEM", phase, details, list(evidence_refs or [])))


def decision_event_type(decision: str) -> str:
    return {"APPROVE": "PROMOTION_APPROVED", "REJECT": "PROMOTION_REJECTED",
            "DEFER": "PROMOTION_DEFERRED"}[decision]
