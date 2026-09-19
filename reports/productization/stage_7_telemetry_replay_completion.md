# Stage 7 — Historical Telemetry Replay Foundation (completion report)

## 1. Baseline before implementation

```
Backend tests:      308/308 PASS
Frontend tests:     27/27 PASS
Protocol freeze:    20/20 PASS
Protected artefacts: 20/20 byte-identical
```

The frozen baseline was re-verified at the start of Stage 7. The
replay engine does not modify any v1 artefact.

## 2. Actual source artefacts used

Single source artefact:

```
artifacts/research_tables/final_predictions.csv
```

Schema (frozen, validated at load time):

```
timestamp,target,model,prediction,actual,absolute_error
```

- 13,176 rows total (1464 hourly rows × 3 targets, with two model
  rows per target where the strongest external benchmark is also
  recorded).
- 1,464 unique timestamps from `2020-11-01 00:00:00` to
  `2020-12-31 23:00:00`.
- Targets: `load`, `wind`, `pv`.
- Models per target: reference (random_forest / hist_gradient_boosting)
  and the strongest external benchmark (RTS_DAY_AHEAD for load/wind;
  H24_DAILY_PERSISTENCE for pv); plus an `mlp` challenger for all
  three.

SHA-256 of the source (recorded in every manifest):

```
8ad40ff5aad1dcd7aff2895e7659efdef25f5069816381f6f363837b4e7dc964
```

This matches the entry in `artifacts/ui_build/phase19_integrity_baseline.json`,
so the source is byte-identical to its recorded baseline.

## 3. Replay architecture

```
src/smartgrid_mlops/replay/
├── __init__.py     # public exports
├── schemas.py      # TelemetryReplayEvent, Target, ReplayMode, EVENT_SOURCE
├── loader.py       # ReplayRow, load_rows, validate_columns, filter_target
├── engine.py       # ReplayEngine, ReplayRun, chronology guard, pacing
└── manifest.py     # ReplayManifest, new_run_id, write_manifest, write_events_jsonl

scripts/
└── replay_telemetry.py   # CLI

artifacts/v2/                       # NEW v2 namespace
├── telemetry_replay/
│   ├── manifests/                  # per-run JSON manifest
│   ├── events/                     # JSONL event stream
│   └── summaries/                  # reserved for future stages
└── experiments/                    # reserved for future stages

tests/
└── test_replay.py                  # 35 tests, all PASS
```

The engine is a pure in-process Python iterator. It does not spawn
threads, does not open network sockets, does not introduce a message
queue, and does not require any new infrastructure. The "event
stream" is a Python generator.

## 4. Event schema

```python
@dataclass(frozen=True)
class TelemetryReplayEvent:
    event_id: str                    # "tr-<uuid>"
    source_timestamp: str            # original observation time
    replay_timestamp: str            # when the simulator emitted it
    target: Literal["load","wind","pv"]
    model: str
    prediction: float
    actual: float
    absolute_error: float
    source: str = "historical_replay"  # always this literal
```

Sample JSONL line:

```json
{"event_id": "tr-...", "source_timestamp": "2020-11-01 00:00:00", "replay_timestamp": "2026-09-05T03:52:38.091828+00:00", "target": "load", "model": "RTS_DAY_AHEAD", "prediction": 3085.154897, "actual": 3001.370949, "absolute_error": 83.783948, "source": "historical_replay"}
```

## 5. Chronological guarantees

- The engine validates chronology **before** any sorting. The
  `_validate_chronology` function walks the source rows as-loaded and
  raises `ReplayChronologyError` on the first non-monotonic timestamp
  per target. The engine never silently reorders.
- The real artefact is chronologically ordered; the validator passes
  for it.
- Across targets, the source uses the same timestamps for all three;
  the global emit order is `(timestamp, target, model)`, which is
  deterministic.
- A test (`test_engine_rejects_non_chronological_source`) constructs
  a synthetic CSV with `01:00:00` followed by `00:00:00` for the
  same target and asserts `ReplayChronologyError`.

## 6. Replay modes

- `fast` (canonical test mode) — events emitted as fast as the
  consumer can read. `replay_timestamp` advances by wall-clock
  microseconds.
- `paced` — sleep `interval` seconds between emissions.
  `replay_timestamp` advances by the actual sleep duration. Paced
  mode requires `interval > 0`; the constructor rejects `0` or
  negative.

## 7. CLI commands

Canonical command (regression):

```bash
.venv\Scripts\python.exe scripts/replay_telemetry.py --target load --mode fast --limit 5
```

Other invocations:

```bash
# All targets, paced
.venv\Scripts\python.exe scripts/replay_telemetry.py --target all --mode paced --interval 1.0

# No events file (manifest only)
.venv\Scripts\python.exe scripts/replay_telemetry.py --target load --mode fast --limit 3 --no-persist

# Override the source artefact
.venv\Scripts\python.exe scripts/replay_telemetry.py --source /path/to/other.csv --mode fast
```

The CLI prints the source SHA-256, target, mode, run id, output
directory, and a final `NOTE: HISTORICAL REPLAY. NOT LIVE TELEMETRY.`
on every invocation.

## 8. Test results

```
tests/test_replay.py            35/35 PASS
tests/ (full backend)          343/343 PASS (308 prior + 35 replay)
product/frontend vitest        27/27 PASS
npx tsc -b                     PASS
```

35 replay tests broken down:

- Schema: 4
- Loading: 7 (covers missing artefact, empty data, missing columns,
  unsupported target, malformed number, target filter)
- Chronology: 4 (real artefact chronological; engine preserves order;
  non-chronological source rejected; empty filter fails explicitly)
- Replay: 12 (fast mode, limit, target filters for all 3 targets,
  no-target means all, unique event ids, paced mode respects
  interval, paced mode rejects zero interval, mode validation,
  limit validation, etc.)
- Determinism: 1 (same source → same chronology AND same numeric
  values)
- Integrity: 3 (SHA-256 recorded; source unchanged; no protected
  Phase 19 artefact modified)
- Isolation: 2 (replay writes only under `artifacts/v2/`)
- CLI: 3 (fast+limit, `--no-persist`, missing source exits 2)

## 9. Integrity verification

After Stage 7 implementation, re-verified:

```
PHASE19_ARTIFACTS: 20 unchanged / 0 changed
FREEZE:            20 PASS / 0 FAIL / 3 skipped
```

The integrity test in the replay suite hashes every file under
`artifacts/research_tables/`, `artifacts/final_evaluation/`,
`artifacts/model_registry/`, and `artifacts/mlops/` before and after a
full replay and asserts byte-identity. It passed.

The CLI's `--out` path is not constrained to `artifacts/v2/`; the
isolation test asserts that no replay output escapes the requested
directory.

## 10. Files created

- `src/smartgrid_mlops/replay/__init__.py` (re-exports)
- `src/smartgrid_mlops/replay/schemas.py`
- `src/smartgrid_mlops/replay/loader.py`
- `src/smartgrid_mlops/replay/engine.py`
- `src/smartgrid_mlops/replay/manifest.py`
- `scripts/replay_telemetry.py`
- `tests/test_replay.py`
- `docs/productization/historical_telemetry_replay.md`
- `reports/productization/stage_7_telemetry_replay_completion.md` (this file)
- `artifacts/v2/telemetry_replay/{manifests,events,summaries}/` (v2
  namespace; v1 artefacts untouched)
- `artifacts/v2/experiments/` (reserved)

## 11. Files modified

None. The v1 tree is byte-identical to the pre-Stage-7 baseline. The
`src/smartgrid_mlops/__init__.py` was NOT modified; the new package
sits alongside the existing productization, agents, governance, mlops,
monitoring, and research subpackages.

## 12. Explicit non-goals

The Stage 7 foundation does NOT, by design:

- connect to monitoring detectors,
- modify the governance policy,
- invoke retraining,
- add model serving,
- add live APIs,
- change the frontend,
- introduce LLM agents,
- add Kafka, Redis, RabbitMQ, MQTT, Celery, PostgreSQL, MongoDB,
  Kubernetes, Docker, cloud queues, WebSockets, or streaming services.

The integration boundary is the in-process `events()` iterator on
`ReplayEngine`. Future Stage 8 will connect it to incremental
monitoring.

## 13. Honest terminology

The product uses these terms:

- Historical telemetry replay
- Simulated event stream
- Paced replay
- Accelerated historical replay
- Offline streaming simulation

The product does NOT use these terms:

- Live telemetry
- Real-time grid feed
- Production streaming system
- Live power-grid monitoring
- Operational smart-grid control
- Quantum / QML / GNN

The literal string `HISTORICAL REPLAY` appears in every CLI run
header and every run manifest. The literal string `NOT LIVE TELEMETRY`
appears at the end of every CLI run. The string `historical_replay`
is the value of every event's `source` field.

## 14. Remaining gaps

- **No consumer beyond the CLI**: Stage 7 is the foundation only. A
  consumer that turns replay events into incremental monitoring
  signals is Stage 8.
- **No streaming-pacing backpressure**: a slow consumer in `fast` mode
  will simply lag the wall clock; in `paced` mode the sleep is
  uninterruptible. Acceptable for the foundation; future stages may
  add cancellation.
- **CLI does not stream the events to stdout** (only the manifest
  path). The JSONL is the canonical output. Adding `--stdout` is a
  trivial extension if a future stage needs it.
- **No summary aggregator**: `artifacts/v2/telemetry_replay/summaries/`
  is reserved but empty. Stage 8 may add per-run summaries.

## 15. Final verdict

Stage 7 is **complete**:

- ✓ Historical data/artefacts are genuinely used (the frozen
  `final_predictions.csv`).
- ✓ No fake measurements are invented.
- ✓ Events replay chronologically (validator fires before any
  reorder).
- ✓ Fast deterministic mode works.
- ✓ Pacing works (`interval > 0` enforced).
- ✓ CLI works (canonical command + 2 mode combinations + 1
  no-persist variant).
- ✓ Replay manifests are generated under `artifacts/v2/`.
- ✓ Source hashes are recorded in every manifest.
- ✓ Source artefacts remain unchanged (proven by integrity test
  hashing every protected file before and after).
- ✓ New outputs are isolated under `artifacts/v2/`.
- ✓ Existing Phase 19 artefacts remain byte-identical (20/20).
- ✓ Protocol freeze remains 20/20 PASS.
- ✓ Existing backend tests still pass (308/308).
- ✓ Existing frontend tests still pass (27/27).
- ✓ New replay tests pass (35/35).
- ✓ Documentation exists (`docs/productization/historical_telemetry_replay.md`).
- ✓ Completion report exists (this file).
- ✓ No live infrastructure was added.
- ✓ No Quantum/QML was introduced.
