"""Telemetry Replay schemas.

The replay contract is a thin, typed wrapper around the existing frozen
prediction artefacts. Every replay event is derived from one row of
`artifacts/research_tables/final_predictions.csv` (1464 hourly rows per
target across LOAD / WIND / PV). The replay engine does not invent
measurements, predictions, or timestamps; it only labels and emits what
the source artefact already contains.

Two timestamps are tracked per event:
  * `source_timestamp` is the original historical observation timestamp
    (the time the measurement was taken, in the dataset).
  * `replay_timestamp` is the wall-clock time the simulator emitted the
    event. In `fast` mode it is monotonic but tight; in `paced` mode it
    is offset by the pacing interval. It is NOT a real measurement.

The `source` field is the literal string `historical_replay`. This makes
it impossible to confuse replay events with anything else in the system.

Stage 7 does not connect the replay stream to monitoring detectors,
governance, agents, or the API. Future Stage 8 will. Stage 7 only
guarantees that the event stream is well-typed, chronologically
ordered, deterministic, and reproducible.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

Target = Literal["load", "wind", "pv"]
SUPPORTED_TARGETS: tuple[Target, ...] = ("load", "wind", "pv")
ReplayMode = Literal["fast", "paced"]
SUPPORTED_MODES: tuple[ReplayMode, ...] = ("fast", "paced")
EVENT_SOURCE = "historical_replay"


@dataclass(frozen=True)
class TelemetryReplayEvent:
    """One historical observation emitted by the replay engine.

    All numeric fields are derived from a single row of the frozen
    `final_predictions.csv` artefact. The replay engine does not
    fabricate any value."""
    event_id: str
    source_timestamp: str     # ISO-8601, original observation time
    replay_timestamp: str     # ISO-8601, when the simulator emitted it
    target: Target
    model: str
    prediction: float
    actual: float
    absolute_error: float
    source: str = field(default=EVENT_SOURCE)

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "source_timestamp": self.source_timestamp,
            "replay_timestamp": self.replay_timestamp,
            "target": self.target,
            "model": self.model,
            "prediction": self.prediction,
            "actual": self.actual,
            "absolute_error": self.absolute_error,
            "source": self.source,
        }


def new_replay_event_id() -> str:
    """Generate a new event id. Uses uuid4 with a `tr-` prefix so replay
    events are easy to grep in audit logs without colliding with
    production event ids."""
    return f"tr-{uuid4()}"


def now_iso() -> str:
    """UTC wall-clock as ISO-8601. Used for `replay_timestamp`; not a
    measurement of anything physical."""
    return datetime.now(timezone.utc).isoformat()
