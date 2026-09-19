#!/usr/bin/env python3
"""Historical Telemetry Replay CLI (Stage 7).

Replays existing historical forecasting observations as a simulated
event stream. NOT live telemetry, NOT real-time grid monitoring.

The source artefact is `artifacts/research_tables/final_predictions.csv`
(1464 hourly rows per target across LOAD / WIND / PV). The replay
engine never modifies the source; it only labels and emits each row as
a typed `TelemetryReplayEvent`.

Modes:
  * `fast`   - emit events immediately (canonical test mode).
  * `paced`  - sleep `--interval` seconds between emissions.

Outputs (optional):
  * `artifacts/v2/telemetry_replay/manifests/<run_id>.json` - per-run
    manifest with source SHA-256, target, mode, count, timestamps.
  * `artifacts/v2/telemetry_replay/events/<run_id>.jsonl`     -
    one event per line, JSONL.

Usage:
  python scripts/replay_telemetry.py --target LOAD --mode fast --limit 10
  python scripts/replay_telemetry.py --target pv --mode paced --interval 1.0
"""
from __future__ import annotations
import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from smartgrid_mlops.replay import (
    DEFAULT_SOURCE_REL,
    ReplayEngine,
    ReplayRun,
    new_run_id,
    sha256_of,
    write_events_jsonl,
    write_manifest,
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
    override = os.environ.get("SMARTGRID_MLOPS_PROJECT_ROOT") or os.environ.get("QSMLOPS_PROJECT_ROOT")
    if override:
        return Path(override).resolve()
    return ROOT


def _resolve_source(source_arg: str | None, project_root: Path) -> Path:
    if source_arg:
        return Path(source_arg).resolve()
    return (project_root / DEFAULT_SOURCE_REL).resolve()


def _resolve_out_dir(out_arg: str | None, project_root: Path) -> Path:
    if out_arg:
        return Path(out_arg).resolve()
    return (project_root / "artifacts" / "v2" / "telemetry_replay").resolve()


def main() -> int:
    p = argparse.ArgumentParser(
        description="Historical telemetry replay. Simulated event stream, not live.")
    p.add_argument("--target", choices=["load", "wind", "pv", "all"], default="all",
                   help="Forecast target to replay. Default: all (LOAD, WIND, PV).")
    p.add_argument("--mode", choices=["fast", "paced"], default="fast",
                   help="fast = emit immediately; paced = sleep --interval seconds.")
    p.add_argument("--interval", type=float, default=1.0,
                   help="Seconds between emissions in paced mode. Default 1.0.")
    p.add_argument("--limit", type=int, default=None,
                   help="Maximum number of events to emit. Default: no limit.")
    p.add_argument("--source", default=None,
                   help="Override the source CSV path. Default: artifacts/research_tables/final_predictions.csv.")
    p.add_argument("--out", default=None,
                   help="Override the v2 output directory. Default: artifacts/v2/telemetry_replay/")
    p.add_argument("--no-persist", action="store_true",
                   help="Do not write the events JSONL; only the manifest is written.")
    args = p.parse_args()

    project_root = _resolve_root()
    source_path = _resolve_source(args.source, project_root)
    if not source_path.is_file():
        LOGGER.error(f"FAIL: source artefact not found: {source_path}")
        return 2
    source_sha = sha256_of(source_path)

    target = None if args.target == "all" else args.target  # type: ignore[assignment]
    out_dir = _resolve_out_dir(args.out, project_root)
    manifests_dir = out_dir / "manifests"
    events_dir = out_dir / "events"

    run_id = new_run_id()
    run = ReplayRun(
        source_path=str(source_path),
        target=target,
        mode=args.mode,
        interval_seconds=args.interval,
        limit=args.limit,
        source_sha256=source_sha,
        run_id=run_id,
    )

    engine = ReplayEngine(run)
    collected: list[TelemetryReplayEvent] = []
    first_ts: str | None = None
    last_ts: str | None = None

    print("SOURCE: HISTORICAL REPLAY")
    print(f"  source_path:     {source_path}")
    print(f"  source_sha256:   {source_sha}")
    print(f"  target:          {args.target}")
    print(f"  mode:            {args.mode.upper()}")
    print(f"  interval_seconds: {args.interval}")
    print(f"  limit:           {args.limit if args.limit is not None else '(none)'}")
    print(f"  run_id:          {run_id}")
    print(f"  out_dir:         {out_dir}")
    print("")

    try:
        for event in engine.events():
            collected.append(event)
            if first_ts is None:
                first_ts = event.source_timestamp
            last_ts = event.source_timestamp
    except Exception as e:
        LOGGER.error(f"FAIL: replay aborted: {type(e).__name__}: {e}")
        return 1

    events_path: Path | None = None
    if not args.no_persist:
        events_path = events_dir / f"{run_id}.jsonl"
        write_events_jsonl(collected, events_path)

    def _relpath(p: Path) -> str:
        """Return a string path; prefer relative to the project root if
        possible, else absolute. This is purely cosmetic for the manifest;
        downstream tools should not assume the path is project-relative."""
        try:
            return str(p.relative_to(project_root))
        except ValueError:
            return str(p)

    artifacts_written: list[str] = []
    if events_path is not None:
        artifacts_written.append(_relpath(events_path))
    manifest_path = write_manifest(
        run,
        out_dir=manifests_dir,
        event_count=len(collected),
        first_source_ts=first_ts,
        last_source_ts=last_ts,
        artifacts_written=artifacts_written,
        completed_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
    )
    artifacts_written.insert(0, _relpath(manifest_path))

    print(f"EVENTS EMITTED: {len(collected)}")
    if collected:
        print(f"  first_source_timestamp: {first_ts}")
        print(f"  last_source_timestamp:  {last_ts}")
    print(f"  manifest: {manifest_path}")
    if events_path is not None:
        print(f"  events:   {events_path}")
    print("NOTE: HISTORICAL REPLAY. NOT LIVE TELEMETRY.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
