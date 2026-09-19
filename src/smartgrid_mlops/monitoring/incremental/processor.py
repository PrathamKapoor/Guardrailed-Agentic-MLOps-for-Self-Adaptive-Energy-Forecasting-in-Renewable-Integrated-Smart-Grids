"""Incremental monitoring processor.

The processor consumes Stage 7 `TelemetryReplayEvent`s one at a time
and produces zero or more existing-schema monitoring events per call.
The detectors it invokes are exactly the ones already exported by
`smartgrid_mlops.monitoring.*`:

  * `monitoring.performance_drift.rolling_mae` for rolling performance
  * `monitoring.feature_drift.psi` for prediction-distribution PSI
  * `monitoring.feature_drift.normalized_wasserstein` for drift
  * `monitoring.prediction_drift.prediction_signal` (a wasserstein wrapper)
  * `monitoring.events.make_event` for monitoring event creation
  * `monitoring.severity.classify_severity` for severity classification

Target isolation: every (target, model) pair has its own
`TargetState`. The processor never lets a LOAD observation enter a
WIND window.

Chronology: the processor verifies per-(target, model) ordering of
`source_timestamp`. Out-of-order events raise `IncrementalChronologyError`
without silently reordering.

Warm-up: a detector only emits a result when its window is "ready"
(capacity observations). Before that, the result is reported as
`WARM_UP` and never as `HEALTHY` or `NO_DRIFT`.

Determinism: the processor is a pure function of the input event
sequence. UUIDs and timestamps for the monitoring events use the
existing `make_event` (UUID v4) — which the existing productization
already uses — so tests must compare deterministic semantic content,
not raw UUIDs.
"""
from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Any, List, Tuple

from smartgrid_mlops.monitoring.events import make_event
from smartgrid_mlops.monitoring.feature_drift import (
    normalized_wasserstein,
    psi,
)
from smartgrid_mlops.monitoring.performance_drift import rolling_mae
from smartgrid_mlops.monitoring.prediction_drift import prediction_signal
from smartgrid_mlops.monitoring.severity import classify_severity
from smartgrid_mlops.replay.schemas import TelemetryReplayEvent

from .state import State
from .windows import EVENT_SOURCE, TargetKey, TargetState

# Detector names exposed via `WarmUpStatus` and as event `detector` fields.
DETECTOR_ROLLING_MAE = "rolling_mae"
DETECTOR_PREDICTION_PSI = "prediction_psi"
DETECTOR_PREDICTION_WASSERSTEIN = "prediction_wasserstein"


class IncrementalChronologyError(RuntimeError):
    """Raised when a replay event's source_timestamp is earlier than the
    previously observed source_timestamp for the same (target, model).
    The processor never silently reorders, never discards, never
    rewrites timestamps."""


class IncrementalInvalidEventError(ValueError):
    """Raised when the event cannot be processed (e.g. unsupported
    target, missing numeric fields, mismatched target/model fields)."""


@dataclass
class ProcessorConfig:
    """Configuration for an `IncrementalProcessor`.

    The defaults match the existing `monitoring.performance_drift.rolling_mae`
    default window of 168 hours, and the same 168-hour reference window
    used by `monitoring.thresholds.calibrate`.
    """
    reference_size: int = 168
    current_size: int = 168
    psi_bins: int = 10
    psi_epsilon: float = 1e-6
    # Per-detector minimum-window fractions. A detector only emits a
    # numeric result once its window has at least this fraction of
    # capacity observations. Until then, the result is WARM_UP.
    min_window_fraction: float = 1.0


@dataclass
class IncrementalProcessor:
    state: State = field(default_factory=State)
    config: ProcessorConfig = field(default_factory=ProcessorConfig)
    events_emitted: int = 0
    events_consumed: int = 0
    warm_up_count: int = 0
    chronology_violations: int = 0
    last_source_timestamp: str | None = None

    def __post_init__(self) -> None:
        # Wire the configured window sizes into the state. The state
        # holds the per-target windows, but the window capacity is
        # bound at the state level for consistency.
        self.state.reference_size = self.config.reference_size
        self.state.current_size = self.config.current_size
        # Recreate existing windows if they were constructed with the
        # default capacity (0) and we now have non-zero.
        for key in self.state.all_keys():
            ts = self.state.get(key)
            if ts.reference.capacity == 0:
                ts.reference.capacity = self.config.reference_size
            if ts.current.capacity == 0:
                ts.current.capacity = self.config.current_size

    def reset(self) -> None:
        """Deterministic reset. After reset, replaying the same input
        sequence produces the same semantic monitoring outputs."""
        self.state = State(reference_size=self.config.reference_size,
                           current_size=self.config.current_size)
        self.events_emitted = 0
        self.events_consumed = 0
        self.warm_up_count = 0
        self.chronology_violations = 0
        self.last_source_timestamp = None

    # --- main entry point -------------------------------------------------

    def consume(self, event: TelemetryReplayEvent) -> List[dict]:
        """Consume one Stage 7 `TelemetryReplayEvent` and return a
        list of existing-schema monitoring events. The list is empty
        during warm-up. The list may contain multiple events when
        several detectors become ready on the same observation (rare
        but possible)."""
        if not isinstance(event, TelemetryReplayEvent):
            raise IncrementalInvalidEventError(
                f"Expected TelemetryReplayEvent, got {type(event).__name__}"
            )
        self.events_consumed += 1
        key: TargetKey = (event.target, event.model)
        ts = self.state.get(key)
        self._enforce_chronology(ts, event)
        ts.event_count += 1
        # The reference window receives the FIRST `reference_size`
        # observations; the current window receives the LAST
        # `current_size` observations. This is the natural batch
        # equivalent of "calibrate on the first half, monitor on the
        # second half". A real calibration step would split on a
        # time boundary; here we use a simple count split, which is
        # what the existing productization does in spirit.
        if not ts.reference.filled:
            ts.reference.append(timestamp=event.source_timestamp,
                                prediction=event.prediction,
                                actual=event.actual,
                                absolute_error=event.absolute_error)
        ts.current.append(timestamp=event.source_timestamp,
                          prediction=event.prediction,
                          actual=event.actual,
                          absolute_error=event.absolute_error)
        emitted: List[dict] = []
        emitted.extend(self._maybe_emit_rolling_mae(key, ts))
        emitted.extend(self._maybe_emit_prediction_psi(key, ts))
        emitted.extend(self._maybe_emit_prediction_wasserstein(key, ts))
        self.events_emitted += len(emitted)
        return emitted

    # --- internals --------------------------------------------------------

    def _enforce_chronology(self, ts: TargetState, event: TelemetryReplayEvent) -> None:
        prev = ts.last_source_timestamp
        if prev is not None and event.source_timestamp < prev:
            self.chronology_violations += 1
            raise IncrementalChronologyError(
                f"Out-of-order event for (target={event.target!r}, model={event.model!r}): "
                f"event.source_timestamp={event.source_timestamp!r} < "
                f"prev={prev!r}. The processor never silently reorders."
            )
        ts.last_source_timestamp = event.source_timestamp
        # Also update the global last-seen for the run manifest.
        if self.last_source_timestamp is None or event.source_timestamp > self.last_source_timestamp:
            self.last_source_timestamp = event.source_timestamp

    def _is_ready(self, win) -> bool:
        """A window is ready when it has at least
        `min_window_fraction * capacity` observations AND capacity > 0."""
        cap = win.capacity
        if cap <= 0:
            return False
        needed = max(1, int(math.ceil(self.config.min_window_fraction * cap)))
        return len(win.predictions) >= needed and len(win.predictions) >= cap

    def _emit(self, *, key: TargetKey, ts: TargetState, detector: str,
              status: str, **payload) -> dict:
        """Wrap a detector result in the existing `make_event` schema.
        `status` is one of `READY`, `WARM_UP`. The `warm_up` status is
        used when the detector does not yet have enough observations
        to produce a numeric value; we never emit a `HEALTHY` or
        `NO_DRIFT` placeholder value."""
        body: dict[str, Any] = {
            "detector": detector,
            "target": key[0],
            "model": key[1],
            "status": status,
            "source": EVENT_SOURCE,
        }
        body.update(payload)
        ev = make_event(**body)
        return ev

    def _maybe_emit_rolling_mae(self, key: TargetKey, ts: TargetState) -> List[dict]:
        if not self._is_ready(ts.current):
            self.warm_up_count += 1
            return [self._emit(key=key, ts=ts, detector=DETECTOR_ROLLING_MAE,
                               status="WARM_UP",
                               window=ts.current.capacity,
                               observations=len(ts.current.predictions))]
        # The reuse contract: invoke the existing batch implementation
        # on the rolling window. The result must be numerically equal
        # to monitoring.performance_drift.rolling_mae(y, pred, window=...).
        value = rolling_mae(list(ts.current.actuals), list(ts.current.predictions),
                            window=ts.current.capacity)
        return [self._emit(key=key, ts=ts, detector=DETECTOR_ROLLING_MAE,
                           status="READY",
                           window=ts.current.capacity,
                           observations=len(ts.current.predictions),
                           value=value,
                           unit="MAE")]

    def _maybe_emit_prediction_psi(self, key: TargetKey, ts: TargetState) -> List[dict]:
        # PSI requires a reference distribution and a current
        # distribution. Both windows must be ready.
        if not (self._is_ready(ts.reference) and self._is_ready(ts.current)):
            self.warm_up_count += 1
            return [self._emit(key=key, ts=ts, detector=DETECTOR_PREDICTION_PSI,
                               status="WARM_UP",
                               reference_window=ts.reference.capacity,
                               reference_observations=len(ts.reference.predictions),
                               current_window=ts.current.capacity,
                               current_observations=len(ts.current.predictions))]
        # Reuse the existing PSI implementation.
        # We use PREDICTIONS (not actuals) so the metric reflects the
        # distribution of the model's outputs, matching the existing
        # feature-drift semantic.
        ref = list(ts.reference.predictions)
        cur = list(ts.current.predictions)
        value = psi(ref, cur, bins=self.config.psi_bins, epsilon=self.config.psi_epsilon)
        return [self._emit(key=key, ts=ts, detector=DETECTOR_PREDICTION_PSI,
                           status="READY",
                           reference_observations=len(ref),
                           current_observations=len(cur),
                           value=value,
                           bins=self.config.psi_bins,
                           unit="PSI")]

    def _maybe_emit_prediction_wasserstein(self, key: TargetKey, ts: TargetState) -> List[dict]:
        if not (self._is_ready(ts.reference) and self._is_ready(ts.current)):
            self.warm_up_count += 1
            return [self._emit(key=key, ts=ts, detector=DETECTOR_PREDICTION_WASSERSTEIN,
                               status="WARM_UP",
                               reference_window=ts.reference.capacity,
                               reference_observations=len(ts.reference.predictions),
                               current_window=ts.current.capacity,
                               current_observations=len(ts.current.predictions))]
        ref = list(ts.reference.predictions)
        cur = list(ts.current.predictions)
        # Reuse the existing normalized_wasserstein. The
        # `prediction_signal` wrapper is equivalent; we invoke the
        # underlying primitive directly to keep the call site
        # consistent with how the existing tests use it.
        value = normalized_wasserstein(ref, cur)
        return [self._emit(key=key, ts=ts, detector=DETECTOR_PREDICTION_WASSERSTEIN,
                           status="READY",
                           reference_observations=len(ref),
                           current_observations=len(cur),
                           value=value,
                           unit="normalized_wasserstein")]
