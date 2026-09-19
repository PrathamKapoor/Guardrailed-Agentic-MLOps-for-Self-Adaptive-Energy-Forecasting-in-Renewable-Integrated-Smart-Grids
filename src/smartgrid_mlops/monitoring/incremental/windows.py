"""Incremental monitoring — rolling target state.

This module maintains, per (target, model) pair, two bounded
ring-buffers:

  * a *reference* window: the first `reference_size` observations the
    processor consumed for that pair.
  * a *current* window:   the most recent `current_size` observations.

Both buffers preserve insertion order. They are sized at
construction time and do not grow. This mirrors the bounded
`make_windows(window=168, stride=24)` semantics already exported by
`monitoring.windows`, so that an incremental rolling MAE of the
`current` window is numerically identical to a batch
`rolling_mae(current_y, current_pred, window=current_size)` from
`monitoring.performance_drift`.

The state is held in `TargetState`; the public entry point
`IncrementalProcessor.consume` orchestrates updates. Target isolation
is enforced by keying all buffers on the tuple `(target, model)`.
"""
from __future__ import annotations
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Tuple

TargetKey = Tuple[str, str]   # (target, model)
EVENT_SOURCE = "historical_replay_incremental_monitoring"


@dataclass
class _RingWindow:
    """A fixed-size deque of (timestamp, prediction, actual) tuples."""
    predictions: Deque[float] = field(default_factory=deque)
    actuals: Deque[float] = field(default_factory=deque)
    absolute_errors: Deque[float] = field(default_factory=deque)
    timestamps: Deque[str] = field(default_factory=deque)
    capacity: int = 0
    filled: bool = False

    def append(self, *, timestamp: str, prediction: float, actual: float,
               absolute_error: float) -> None:
        self.timestamps.append(timestamp)
        self.predictions.append(prediction)
        self.actuals.append(actual)
        self.absolute_errors.append(absolute_error)
        if self.capacity > 0 and len(self.predictions) > self.capacity:
            self.timestamps.popleft()
            self.predictions.popleft()
            self.actuals.popleft()
            self.absolute_errors.popleft()
        if self.capacity > 0 and len(self.predictions) >= self.capacity:
            self.filled = True

    def is_ready(self) -> bool:
        """A window is "ready" only when it has capacity observations
        AND has reached its declared capacity. Below capacity is a
        warm-up state, never reported as 'healthy'."""
        return self.filled and self.capacity > 0 and len(self.predictions) >= self.capacity

    def snapshot(self) -> dict:
        """Return plain-list snapshots. Used by the detector invocations
        and by tests asserting equivalence with batch implementations."""
        return {
            "timestamps": list(self.timestamps),
            "predictions": list(self.predictions),
            "actuals": list(self.actuals),
            "absolute_errors": list(self.absolute_errors),
        }


@dataclass
class TargetState:
    """Per (target, model) state. Holds the reference and current
    ring windows and the last-seen source timestamp for chronology
    enforcement."""
    target: str
    model: str
    reference: _RingWindow = field(default_factory=_RingWindow)
    current: _RingWindow = field(default_factory=_RingWindow)
    last_source_timestamp: str | None = None
    event_count: int = 0

    def last_event_count(self) -> int:
        return self.event_count
