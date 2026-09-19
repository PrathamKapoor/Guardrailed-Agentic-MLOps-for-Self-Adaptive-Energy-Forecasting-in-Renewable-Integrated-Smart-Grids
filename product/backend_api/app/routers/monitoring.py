"""GET /api/monitoring: read the existing monitoring events.

The productization layer emits 12 events on a one-shot basis from the
frozen final-test evidence. There is no live monitoring; events are
derived from a deterministic view of the research artefacts.
"""
from __future__ import annotations
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from ..dependencies import AppState, get_state
from ..schemas import MonitoringEvent

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])


def _to_event(d: dict) -> MonitoringEvent:
    """Project a raw productization event dict into the Pydantic schema."""
    fields = set(d.keys())
    known = {"event_id", "timestamp", "event_type", "target", "model"}
    extra = {k: v for k, v in d.items() if k not in known}
    return MonitoringEvent(
        event_id=d.get("event_id", ""), timestamp=d.get("timestamp", ""),
        event_type=d.get("event_type", ""), target=d.get("target", ""),
        model=d.get("model", ""), extra=extra,
    )


@router.get("/events", response_model=list[MonitoringEvent],
            summary="Read the productization-layer monitoring events derived from the frozen final-test artefacts")
def list_events(event_type: Optional[str] = None, target: Optional[str] = None,
                 state: AppState = Depends(get_state)) -> list[MonitoringEvent]:
    out = []
    for raw in state.signals:
        if event_type and raw.get("event_type") != event_type:
            continue
        if target and raw.get("target") != target:
            continue
        out.append(_to_event(raw))
    if not out and (event_type or target):
        # Not an error; the query is just filtered to nothing.
        return []
    return out


@router.get("/events/{event_id}", response_model=MonitoringEvent,
            summary="Get a single monitoring event by event_id")
def get_event(event_id: str, state: AppState = Depends(get_state)) -> MonitoringEvent:
    for raw in state.signals:
        if raw.get("event_id") == event_id:
            return _to_event(raw)
    raise HTTPException(status_code=404, detail=f"Unknown event_id {event_id!r}")


@router.get("/drift", response_model=list[MonitoringEvent],
            summary="Drift events (event_type starts with feature_/prediction_/performance_/model_health) from the frozen productization layer")
def list_drift(state: AppState = Depends(get_state)) -> list[MonitoringEvent]:
    out = []
    for raw in state.signals:
        if any(raw.get("event_type", "").startswith(prefix)
                for prefix in ("performance_", "prediction_", "model_health", "data_quality")):
            out.append(_to_event(raw))
    return out
