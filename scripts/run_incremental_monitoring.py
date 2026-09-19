#!/usr/bin/env python3
"""Incremental monitoring CLI (Stage 8).

Connects the Stage 7 Historical Telemetry Replay engine to the
incremental monitoring layer. The processor consumes replay events
one at a time and emits existing-schema monitoring events.

The script:

  1. Loads the Stage 7 replay engine over the frozen
     `final_predictions.csv`.
  2. Iterates the events in chronological order.
  3. Feeds each event into the `IncrementalProcessor`.
  4. Writes the per-run monitoring events to
     `artifacts/v2/incremental_monitoring/events/<run_id>.jsonl`.
  5. Writes a run manifest to
     `artifacts/v2/incremental_monitoring/manifests/<run_id>.json`.
  6. Prints a deterministic summary header.

It does NOT connect to governance, retraining, model promotion, or
any lifecycle mutation. Stage 8 stops at monitoring.
"""
from __future__ import annotations
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from smartgrid_mlops.monitoring.incremental import (
    IncrementalProcessor,
    ProcessorConfig,
)
from smartgrid_mlops.replay import (
    DEFAULT_SOURCE_REL,
    ReplayEngine,
    ReplayRun,
    sha256_of,
)
from smartgrid_mlops.replay.schemas import TelemetryReplayEvent
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stderr,
)
LOGGER = logging.getLogger(__name__)


def _resolve_root() -> Path:
    override = os.environ.get("QSMLOPS_PROJECT_ROOT")
    if override:
        return Path(override).resolve()
    return ROOT


def _relpath(p: Path, project_root: Path) -> str:
    try:
        return str(p.relative_to(project_root))
    except ValueError:
        return str(p)


def main() -> int:
    p = argparse.ArgumentParser(
        description="Incremental monitoring over Stage 7 historical telemetry replay.")
    p.add_argument("--target", choices=["load", "wind", "pv", "all"], default="all")
    p.add_argument("--mode", choices=["fast", "paced"], default="fast")
    p.add_argument("--interval", type=float, default=1.0)
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--source", default=None)
    p.add_argument("--out", default=None,
                   help="Override the v2 output directory. Default: artifacts/v2/incremental_monitoring/")
    p.add_argument("--reference-size", type=int, default=168,
                   help="Reference window size in events. Default 168 (matches existing rolling_mae).")
    p.add_argument("--current-size", type=int, default=168,
                   help="Current window size in events. Default 168.")
    p.add_argument("--no-persist", action="store_true",
                   help="Do not write the events JSONL; only the manifest is written.")
    args = p.parse_args()

    project_root = _resolve_root()
    source_path = Path(args.source).resolve() if args.source else (project_root / DEFAULT_SOURCE_REL).resolve()
    if not source_path.is_file():
        LOGGER.error(f"FAIL: source artefact not found: {source_path}")
        return 2
    source_sha = sha256_of(source_path)

    target = None if args.target == "all" else args.target
    out_dir = Path(args.out).resolve() if args.out else (project_root / "artifacts" / "v2" / "incremental_monitoring").resolve()
    manifests_dir = out_dir / "manifests"
    events_dir = out_dir / "events"
    summaries_dir = out_dir / "summaries"

    run_id = f"imr-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}-{os.urandom(3).hex()}"
    run = ReplayRun(
        source_path=str(source_path),
        target=target,
        mode=args.mode,
        interval_seconds=args.interval,
        limit=args.limit,
        source_sha256=source_sha,
        run_id=run_id,
    )

    processor = IncrementalProcessor(
        config=ProcessorConfig(reference_size=args.reference_size,
                               current_size=args.current_size),
    )

    print("SOURCE MODE: HISTORICAL REPLAY")
    print("LIVE TELEMETRY: NOT USED")
    LOGGER.info(f"  source_path:    {source_path}")
    LOGGER.info(f"  source_sha256:  {source_sha}")
    LOGGER.info(f"  target:         {args.target}")
    LOGGER.info(f"  mode:           {args.mode}")
    LOGGER.info(f"  limit:          {args.limit if args.limit is not None else '(none)'}")
    LOGGER.info(f"  reference_size: {args.reference_size}")
    LOGGER.info(f"  current_size:   {args.current_size}")
    LOGGER.info(f"  run_id:         {run_id}")
    LOGGER.info(f"  out_dir:        {out_dir}")
    LOGGER.info("")

    engine = ReplayEngine(run)
    emitted_events: list[dict] = []
    first_source_ts: str | None = None
    last_source_ts: str | None = None
    chronology_violations = 0
    error: str | None = None

    try:
        for event in engine.events():
            if first_source_ts is None:
                first_source_ts = event.source_timestamp
            last_source_ts = event.source_timestamp
            new_events = processor.consume(event)
            emitted_events.extend(new_events)
    except Exception as e:
        error = f"{type(e).__name__}: {e}"
        chronology_violations = processor.chronology_violations
        LOGGER.error(f"FAIL: {error}")
    chronology_violations = processor.chronology_violations

    events_path: Path | None = None
    if not args.no_persist and emitted_events:
        events_path = events_dir / f"{run_id}.jsonl"
        events_dir.mkdir(parents=True, exist_ok=True)
        with events_path.open("w", encoding="utf-8") as f:
            for e in emitted_events:
                f.write(json.dumps(e, sort_keys=True) + "\n")

    artifacts_written: list[str] = []
    if events_path is not None:
        artifacts_written.append(_relpath(events_path, project_root))

    manifest = {
        "run_id": run_id,
        "mode": "historical_replay_incremental_monitoring",
        "source_path": str(source_path),
        "source_sha256": source_sha,
        "target": args.target,
        "replay_mode": args.mode,
        "limit": args.limit,
        "reference_size": args.reference_size,
        "current_size": args.current_size,
        "events_consumed": processor.events_consumed,
        "monitoring_events_emitted": processor.events_emitted,
        "warm_up_count": processor.warm_up_count,
        "chronology_violations": chronology_violations,
        "first_source_timestamp": first_source_ts,
        "last_source_timestamp": last_source_ts,
        "started_at": run.started_at,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "artifacts_written": artifacts_written,
        "error": error,
        "notes": "Historical replay + incremental monitoring. Not live.",
    }
    summaries_dir.mkdir(parents=True, exist_ok=True)
    summary_path = summaries_dir / f"{run_id}.json"
    summary_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                            encoding="utf-8")
    manifest_path = manifests_dir / f"{run_id}.json"
    manifests_dir.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                             encoding="utf-8")
    artifacts_written.insert(0, _relpath(manifest_path, project_root))
    artifacts_written.insert(1, _relpath(summary_path, project_root))

    print(f"EVENTS CONSUMED: {processor.events_consumed}")
    print(f"MONITORING EVENTS EMITTED: {processor.events_emitted}")
    LOGGER.info(f"WARM-UP DETECTOR EVALUATIONS: {processor.warm_up_count}")
    if first_source_ts:
        LOGGER.info(f"  first_source_timestamp: {first_source_ts}")
        LOGGER.info(f"  last_source_timestamp:  {last_source_ts}")
    LOGGER.info(f"  manifest: {manifest_path}")
    LOGGER.info(f"  summary:  {summary_path}")
    if events_path is not None:
        LOGGER.info(f"  events:   {events_path}")
    if chronology_violations:
        LOGGER.info(f"CHRONOLOGY VIOLATIONS: {chronology_violations}")
    print("NOTE: HISTORICAL REPLAY + INCREMENTAL MONITORING. NOT LIVE.")
    return 0 if error is None else 1


if __name__ == "__main__":
    sys.exit(main())
