"""Phase 17 agent audit events: extend the append-oriented audit log."""
from __future__ import annotations
import json
from pathlib import Path
from smartgrid_mlops.mlops.audit import append_audit_event
from smartgrid_mlops.mlops.schemas import AuditEvent
from .schemas import AGENT_AUDIT_EVENT_TYPES, FORBIDDEN_AUDIT_EVENT_TYPES


def emit(path: Path, event_type: str, subject_id: str, details: dict, evidence_refs=None, phase: str = "17") -> None:
    if event_type in FORBIDDEN_AUDIT_EVENT_TYPES:
        raise ValueError(f"FORBIDDEN_AGENT_EVENT: {event_type} must never be emitted")
    if event_type not in AGENT_AUDIT_EVENT_TYPES:
        raise ValueError(f"Unknown agent audit event {event_type}")
    append_audit_event(Path(path), AuditEvent(event_type, subject_id, "AGENT", phase, details, list(evidence_refs or [])))


def read_agent_events(path: Path) -> list[dict]:
    p = Path(path)
    if not p.exists(): return []
    events = [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]
    return [e for e in events if e.get("event_type") in AGENT_AUDIT_EVENT_TYPES and e.get("phase") == "17"]
