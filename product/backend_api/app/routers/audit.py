"""GET /api/audit: read the existing evidence ledger (append-only JSONL).

No second audit ledger. The endpoint just reads `artifacts/mlops/audit/events.jsonl`
and exposes it as Pydantic.
"""
from __future__ import annotations
import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from ..dependencies import AppState, get_state
from ..schemas import AuditChainVerification, AuditEvent

router = APIRouter(prefix="/api/audit", tags=["audit"])


def _iter_events(path) -> list[dict]:
    if not path.exists():
        return []
    out: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


@router.get("/events", response_model=list[AuditEvent],
            summary="Existing evidence-ledger events (read-only)")
def list_audit_events(event_type: Optional[str] = None, subject: Optional[str] = None,
                     limit: int = 100, state: AppState = Depends(get_state)) -> list[AuditEvent]:
    path = state.project_root / "artifacts/mlops/audit/events.jsonl"
    out: list[AuditEvent] = []
    for entry in _iter_events(path):
        record = entry.get("record", entry)  # tolerate both wrapped and bare
        if event_type and record.get("type", entry.get("type")) != event_type:
            continue
        if subject and record.get("subject_id", entry.get("subject_id")) != subject:
            continue
        out.append(AuditEvent(
            seq=entry.get("seq"), timestamp=entry.get("timestamp", record.get("timestamp", "")),
            type=record.get("type", entry.get("type", "")),
            record=record,
        ))
        if len(out) >= limit:
            break
    return out


@router.get("/verify", response_model=AuditChainVerification,
            summary="Verify the existing evidence-ledger JSONL (each line is well-formed JSON; the ledger is append-only)")
def verify_chain(state: AppState = Depends(get_state)) -> AuditChainVerification:
    """The existing evidence ledger is an append-only JSONL file
    (`artifacts/mlops/audit/events.jsonl`). There is no hash chain in the
    existing implementation. The endpoint verifies that every line is valid
    JSON and reports the count + the first/last timestamps."""
    path = state.project_root / "artifacts/mlops/audit/events.jsonl"
    if not path.exists():
        return AuditChainVerification(chain_ok=False, message=f"ledger missing: {path}", head="")
    n_ok = 0
    first_ts = ""
    last_ts = ""
    bad: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError as exc:
            bad.append(str(exc))
            continue
        n_ok += 1
        ts = entry.get("timestamp", "")
        if not first_ts:
            first_ts = ts
        last_ts = ts or last_ts
    ok = not bad
    head = f"n_events={n_ok}"
    if bad:
        head = f"{head}; bad_lines={len(bad)}"
    msg = "OK" if ok else f"invalid JSON lines: {bad[:3]}"
    return AuditChainVerification(chain_ok=ok, message=msg, head=head)
