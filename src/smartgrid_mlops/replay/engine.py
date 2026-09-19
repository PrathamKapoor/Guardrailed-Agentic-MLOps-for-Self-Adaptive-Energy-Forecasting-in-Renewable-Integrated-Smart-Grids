"""Replay engine.

The engine is a Python iterator over chronologically-ordered
`TelemetryReplayEvent` instances. It does not spawn threads, does not
open network sockets, does not write to the source artefact, and does
not connect to monitoring detectors. It is a pure in-process generator.

Chronology: events are emitted in the order they appear in the source
artefact, after a per-target sort by `source_timestamp`. The chronology
invariant is verified before iteration begins; if a target's rows are
not in non-decreasing timestamp order, the engine raises and emits
nothing. This avoids silent reordering.

Pacing:
  * `fast` mode emits events as quickly as the consumer can read them.
    The `replay_timestamp` is taken at emission time; successive events
    are monotonic but may be microseconds apart. This is the canonical
    test mode.
  * `paced` mode sleeps `interval` seconds between emissions. The
    `replay_timestamp` advances by the actual sleep duration. This is
    NOT real-time telemetry; it is paced historical replay.
"""
from __future__ import annotations
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterator, Sequence

from .loader import ReplayRow, filter_target, load_rows
from .schemas import (
    EVENT_SOURCE,
    ReplayMode,
    SUPPORTED_MODES,
    Target,
    TelemetryReplayEvent,
    new_replay_event_id,
    now_iso,
)


class ReplayChronologyError(RuntimeError):
    """Raised when a target's source rows are not in non-decreasing
    timestamp order. The engine never silently reorders."""


class ReplayEmptyError(RuntimeError):
    """Raised when the requested target produces zero rows. The engine
    refuses to emit an empty event stream as a successful run."""


def _parse_ts(s: str) -> datetime:
    """Parse a `YYYY-MM-DD HH:MM:SS` string. The frozen artefact uses
    this exact format; we do not accept alternative parsers."""
    return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")


@dataclass(frozen=True)
class ReplayRun:
    """Configuration for a single replay run. Constructed by the CLI and
    by tests; the engine itself is stateless beyond this object."""
    source_path: str
    target: Target | None = None
    mode: ReplayMode = "fast"
    interval_seconds: float = 1.0
    limit: int | None = None
    source_sha256: str = ""
    run_id: str = ""
    on_event: Callable[[TelemetryReplayEvent], None] | None = None
    persist_path: str | None = None
    started_at: str = field(default_factory=now_iso)

    def __post_init__(self) -> None:
        if self.mode not in SUPPORTED_MODES:
            raise ValueError(
                f"Unsupported replay mode {self.mode!r}. "
                f"Expected one of {SUPPORTED_MODES}."
            )
        if self.mode == "paced" and self.interval_seconds <= 0:
            raise ValueError("Paced mode requires interval_seconds > 0.")
        if self.limit is not None and self.limit <= 0:
            raise ValueError("limit must be positive when set.")


def _validate_chronology(rows: Sequence[ReplayRow]) -> None:
    """Validate the source artefact chronology as-loaded, BEFORE
    any sorting. For each target, the rows must be in non-decreasing
    timestamp order. Raises ReplayChronologyError on the first
    violation. The engine never silently reorders."""
    by_target: dict[str, list[ReplayRow]] = defaultdict(list)
    for r in rows:
        by_target[r.target].append(r)
    for target, group_rows in by_target.items():
        prev: str | None = None
        for i, r in enumerate(group_rows):
            if prev is not None and r.timestamp < prev:
                raise ReplayChronologyError(
                    f"Non-chronological source data for target {target!r}: "
                    f"row[{i}].timestamp={r.timestamp!r} < row[{i - 1}].timestamp={prev!r}. "
                    "The replay engine refuses to silently reorder."
                )
            prev = r.timestamp


def _group_by_target(rows: Sequence[ReplayRow]) -> dict[str, list[ReplayRow]]:
    """Group rows by target. Chronology is verified separately in
    _validate_chronology; the real artefact is already chronologically
    ordered, so this is a stable pass-through."""
    grouped: dict[str, list[ReplayRow]] = defaultdict(list)
    for r in rows:
        grouped[r.target].append(r)
    return dict(grouped)


class ReplayEngine:
    """Iterate one `TelemetryReplayEvent` at a time, in chronological
    order. The engine does not mutate the source artefact and does not
    persist events unless an explicit `persist_path` is set on the
    `ReplayRun`.

    Usage:
        engine = ReplayEngine(run)
        for event in engine.events():
            ...
    """

    def __init__(self, run: ReplayRun) -> None:
        self.run = run

    def events(self) -> Iterator[TelemetryReplayEvent]:
        rows = load_rows(Path(self.run.source_path))
        # The `target` field on ReplayRun is `None` to mean "all targets"
        # and a string for a specific target. The CLI normalises "all"
        # to None before constructing the run. Tests that pass the
        # literal string "all" are also accepted here as a convenience.
        target = self.run.target
        if target == "all":  # type: ignore[comparison-overlap]
            target = None
        rows = filter_target(rows, target)
        if not rows:
            raise ReplayEmptyError(
                f"No rows for target={self.run.target!r} in {self.run.source_path}. "
                "Replay refuses to emit an empty event stream."
            )
        # Validate chronology BEFORE any sorting. This is the only way to
        # catch a malformed source that contains, e.g., row 5 with an
        # earlier timestamp than row 4 for the same target. The engine
        # never silently reorders.
        _validate_chronology(rows)
        rows_by_target = _group_by_target(rows)
        # Flatten in chronological order across targets.
        flat: list[ReplayRow] = []
        for target_key in sorted(rows_by_target):
            flat.extend(rows_by_target[target_key])
        # Across targets, the source artefact uses the SAME timestamps
        # for all targets (1464 hourly rows per target), so the global
        # order is well-defined and deterministic. Sort is stable
        # because the per-target ordering is already chronological.
        flat.sort(key=lambda r: (_parse_ts(r.timestamp), r.target, r.model))

        emitted = 0
        for r in flat:
            if self.run.limit is not None and emitted >= self.run.limit:
                return
            if self.run.mode == "paced" and emitted > 0:
                time.sleep(self.run.interval_seconds)
            event = TelemetryReplayEvent(
                event_id=new_replay_event_id(),
                source_timestamp=r.timestamp,
                replay_timestamp=now_iso(),
                target=r.target,  # type: ignore[arg-type]
                model=r.model,
                prediction=r.prediction,
                actual=r.actual,
                absolute_error=r.absolute_error,
                source=EVENT_SOURCE,
            )
            if self.run.on_event is not None:
                self.run.on_event(event)
            emitted += 1
            yield event
