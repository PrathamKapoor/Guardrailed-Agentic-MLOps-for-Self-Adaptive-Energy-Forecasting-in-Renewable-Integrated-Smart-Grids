"""Incremental monitoring (Stage 8).

The incremental layer consumes Stage 7 `TelemetryReplayEvent`s one at
a time and produces existing-schema monitoring events via the
detectors already exported by `smartgrid_mlops.monitoring`:

  * `rolling_mae`        (monitoring.performance_drift)
  * `psi`                (monitoring.feature_drift)
  * `normalized_wasserstein`  (monitoring.feature_drift)
  * `prediction_signal`  (monitoring.prediction_drift, wasserstein wrapper)
  * `make_event`         (monitoring.events) — for monitoring event creation
  * `classify_severity`  (monitoring.severity)

This package does NOT introduce new monitoring math, new metrics, or
new thresholds. It only maintains the rolling state required to feed
the existing detectors incrementally.

Stage 8 stops at monitoring. Future Stage 9+ may connect monitoring
outputs to research workflows. This package does not integrate with
governance, retraining, model promotion, or any lifecycle mutation.
"""
from .state import State
from .windows import (
    EVENT_SOURCE,
    TargetKey,
    TargetState,
)
from .processor import (
    DETECTOR_PREDICTION_PSI,
    DETECTOR_PREDICTION_WASSERSTEIN,
    DETECTOR_ROLLING_MAE,
    IncrementalChronologyError,
    IncrementalInvalidEventError,
    IncrementalProcessor,
    ProcessorConfig,
)

__all__ = [
    "DETECTOR_PREDICTION_PSI",
    "DETECTOR_PREDICTION_WASSERSTEIN",
    "DETECTOR_ROLLING_MAE",
    "EVENT_SOURCE",
    "IncrementalChronologyError",
    "IncrementalInvalidEventError",
    "IncrementalProcessor",
    "ProcessorConfig",
    "State",
    "TargetKey",
    "TargetState",
]
