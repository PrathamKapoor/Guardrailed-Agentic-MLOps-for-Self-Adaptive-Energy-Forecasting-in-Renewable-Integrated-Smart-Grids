"""Replay run manifest.

A manifest records the exact parameters of one replay run: which source
artefact, which target, which mode, how many events were emitted, and
the SHA-256 of the source at run time. This makes experiments
reproducible: a future run with the same parameters and the same source
artefact will produce the same chronology, the same event ids, and the
same numeric values.

The manifest is written under `artifacts/v2/telemetry_replay/manifests/`.
It does NOT touch the v1 frozen artefact tree.
"""
from __future__ import annotations
import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .engine import ReplayRun
from .loader import DEFAULT_SOURCE_REL, sha256_of
from .schemas import TelemetryReplayEvent


@dataclass
class ReplayManifest:
    run_id: str
    source_path: str
    source_sha256: str
    target: str | None
    mode: str
    interval_seconds: float
    limit: int | None
    event_count: int
    first_source_timestamp: str | None
    last_source_timestamp: str | None
    created_at: str
    completed_at: str
    artifacts_written: list[str] = field(default_factory=list)
    notes: str = "Historical telemetry replay. Simulated event stream. Not live."

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def new_run_id() -> str:
    """Unique per run. The format is `trr-<UTC-ISO-date>-<hex>` so that
    manifests sort naturally by creation time and are easy to scan."""
    return f"trr-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}-{hashlib.sha1(str(datetime.now(timezone.utc).isoformat()).encode()).hexdigest()[:8]}"


def write_manifest(
    run: ReplayRun,
    *,
    out_dir: Path,
    event_count: int,
    first_source_ts: str | None,
    last_source_ts: str | None,
    artifacts_written: list[str] | None = None,
    completed_at: str,
) -> Path:
    """Write the manifest to `<out_dir>/<run_id>.json`. Returns the path."""
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = ReplayManifest(
        run_id=run.run_id or new_run_id(),
        source_path=run.source_path,
        source_sha256=run.source_sha256,
        target=run.target,
        mode=run.mode,
        interval_seconds=run.interval_seconds,
        limit=run.limit,
        event_count=event_count,
        first_source_timestamp=first_source_ts,
        last_source_timestamp=last_source_ts,
        created_at=run.started_at,
        completed_at=completed_at,
        artifacts_written=list(artifacts_written or []),
    )
    path = out_dir / f"{manifest.run_id}.json"
    path.write_text(json.dumps(manifest.to_dict(), indent=2, sort_keys=True) + "\n",
                    encoding="utf-8")
    return path


def write_events_jsonl(events: list[TelemetryReplayEvent], path: Path) -> None:
    """Append-friendly JSONL writer. One event per line, sorted keys,
    trailing newline. Idempotent over an existing file? No: it overwrites
    the target file. The CLI calls it once per run with a unique path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for e in events:
            f.write(json.dumps(e.to_dict(), sort_keys=True) + "\n")


def source_default_rel() -> str:
    return DEFAULT_SOURCE_REL
