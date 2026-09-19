"""Historical telemetry replay foundation (Stage 7).

This package replays existing historical forecasting observations as a
simulated event stream. It is NOT a live smart-grid telemetry system.
It is NOT real-time grid monitoring. It is a controlled, deterministic
re-emission of the frozen Phase 19 prediction artefact.

The replay engine writes ONLY to:
  artifacts/v2/telemetry_replay/

The frozen Phase 19 artefact tree (artifacts/research_tables/,
artifacts/final_evaluation/, artifacts/model_registry/, artifacts/mlops/)
is read-only and never modified by this package.

Future Stage 8 may connect this engine to incremental monitoring. The
replay foundation intentionally does not.
"""
from .schemas import (
    EVENT_SOURCE,
    SUPPORTED_MODES,
    SUPPORTED_TARGETS,
    ReplayMode,
    Target,
    TelemetryReplayEvent,
    new_replay_event_id,
    now_iso,
)
from .loader import (
    DEFAULT_SOURCE_REL,
    REQUIRED_COLUMNS,
    ReplayRow,
    filter_target,
    load_rows,
    sha256_of,
    validate_columns,
)
from .engine import (
    ReplayChronologyError,
    ReplayEmptyError,
    ReplayEngine,
    ReplayRun,
)
from .manifest import (
    ReplayManifest,
    new_run_id,
    write_events_jsonl,
    write_manifest,
)

__all__ = [
    "DEFAULT_SOURCE_REL",
    "EVENT_SOURCE",
    "REQUIRED_COLUMNS",
    "ReplayChronologyError",
    "ReplayEmptyError",
    "ReplayEngine",
    "ReplayManifest",
    "ReplayMode",
    "ReplayRow",
    "ReplayRun",
    "SUPPORTED_MODES",
    "SUPPORTED_TARGETS",
    "Target",
    "TelemetryReplayEvent",
    "filter_target",
    "load_rows",
    "new_replay_event_id",
    "new_run_id",
    "now_iso",
    "sha256_of",
    "validate_columns",
    "write_events_jsonl",
    "write_manifest",
]
