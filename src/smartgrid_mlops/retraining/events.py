"""Retraining audit events: extends the Phase 12/13 append-oriented audit log."""
from __future__ import annotations
import json
from pathlib import Path
from smartgrid_mlops.mlops.audit import append_audit_event
from smartgrid_mlops.mlops.schemas import AuditEvent

RETRAINING_EVENT_TYPES = (
    "RETRAINING_REQUEST_CREATED", "RETRAINING_REQUEST_ALLOWED", "RETRAINING_REQUEST_DENIED",
    "RETRAINING_REQUEST_DEFERRED", "RETRAINING_JOB_STARTED", "RETRAINING_JOB_COMPLETED",
    "RETRAINING_JOB_FAILED", "RETRAINED_CANDIDATE_CREATED", "CHALLENGER_REGISTERED",
)


def emit(path: Path, event_type: str, subject_id: str, details: dict, evidence_refs=None, phase: str = "15") -> None:
    if event_type not in RETRAINING_EVENT_TYPES:
        raise ValueError(f"Unknown retraining audit event {event_type}")
    append_audit_event(Path(path), AuditEvent(event_type, subject_id, "SYSTEM", phase, details, list(evidence_refs or [])))


def decision_event_type(decision: str) -> str:
    return {"ALLOW": "RETRAINING_REQUEST_ALLOWED", "DENY": "RETRAINING_REQUEST_DENIED",
            "DEFER": "RETRAINING_REQUEST_DEFERRED"}[decision]


def read_retraining_events(path: Path) -> list[dict]:
    p = Path(path)
    if not p.exists(): return []
    events = [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]
    return [e for e in events if e.get("event_type") in RETRAINING_EVENT_TYPES]
