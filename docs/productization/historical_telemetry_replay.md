# Historical Telemetry Replay (Stage 7)

## 1. What this is

A **Historical Telemetry Replay** foundation that re-emits existing
historical forecasting observations as a simulated event stream. The
source artefact is the frozen `final_predictions.csv` (1464 hourly rows
per target across LOAD / WIND / PV), and the engine emits one typed
`TelemetryReplayEvent` per row in deterministic chronological order.

## 2. What this is NOT

- NOT live smart-grid telemetry.
- NOT real-time grid monitoring.
- NOT streaming production infrastructure.
- NOT live operational control.
- NOT LLM-backed reasoning.
- NOT Quantum/QML.

The system explicitly does not provide live smart-grid telemetry. It
simulates event-by-event arrival of existing historical observations.
The phrase used in every CLI run header and every manifest is
`HISTORICAL REPLAY`.

## 3. Source data / artifact requirements

The replay engine reads a single frozen artefact:

```
artifacts/research_tables/final_predictions.csv
```

Schema (frozen, validated at load time):

```
timestamp,target,model,prediction,actual,absolute_error
```

- `timestamp` is `YYYY-MM-DD HH:MM:SS` and identical across the
  three targets (1464 hourly rows per target).
- `target` ∈ {`load`, `wind`, `pv`}.
- `model` is the model name (e.g. `random_forest`, `mlp`,
  `RTS_DAY_AHEAD`, `hist_gradient_boosting`, `H24_DAILY_PERSISTENCE`).
- `prediction`, `actual`, `absolute_error` are numeric (cast to float).

The engine never substitutes placeholders. Missing columns, malformed
numbers, unsupported targets, or empty data all fail explicitly.

## 4. Replay modes

| Mode | Behaviour |
| --- | --- |
| `fast` | Emit events as fast as the consumer can read them. `replay_timestamp` advances by wall-clock microseconds. Canonical test mode. |
| `paced` | Sleep `interval` seconds between emissions. `replay_timestamp` advances by the actual sleep duration. NOT real-time telemetry; just paced historical replay. |

The optional `accelerated time` mode (e.g. 1 historical hour = 1 real
second) is documented as **accelerated historical replay**, never as
"live streaming".

## 5. CLI usage

```
python scripts/replay_telemetry.py --target LOAD --mode fast --limit 10
python scripts/replay_telemetry.py --target pv --mode paced --interval 1.0
python scripts/replay_telemetry.py --target all --mode fast --limit 100
python scripts/replay_telemetry.py --source /path/to/other.csv --mode fast
```

Arguments:

| Flag | Default | Notes |
| --- | --- | --- |
| `--target` | `all` | `load` / `wind` / `pv` / `all` |
| `--mode` | `fast` | `fast` / `paced` |
| `--interval` | `1.0` | Seconds between emissions in paced mode |
| `--limit` | none | Maximum number of events to emit |
| `--source` | `artifacts/research_tables/final_predictions.csv` | Override source CSV path |
| `--out` | `artifacts/v2/telemetry_replay/` | Override v2 output directory |
| `--no-persist` | false | Skip the events JSONL; only the manifest is written |

Canonical command (regression):

```
.venv\Scripts\python.exe scripts/replay_telemetry.py --target load --mode fast --limit 5
```

Sample output (abridged):

```
SOURCE: HISTORICAL REPLAY
  source_path:     C:\...\artifacts\research_tables\final_predictions.csv
  source_sha256:   8ad40ff5aad1dcd7aff2895e7659efdef25f5069816381f6f363837b4e7dc964
  target:          load
  mode:            fast
  ...

EVENTS EMITTED: 5
  first_source_timestamp: 2020-11-01 00:00:00
  last_source_timestamp:  2020-11-01 01:00:00
  manifest: C:\...\artifacts\v2\telemetry_replay\manifests\trr-...json
  events:   C:\...\artifacts\v2\telemetry_replay\events\trr-...jsonl

NOTE: HISTORICAL REPLAY. NOT LIVE TELEMETRY.
```

## 6. Event schema

`TelemetryReplayEvent`:

```json
{
  "event_id": "tr-<uuid>",
  "source_timestamp": "2020-11-01 00:00:00",
  "replay_timestamp": "2026-09-05T03:52:38.091828+00:00",
  "target": "load",
  "model": "random_forest",
  "prediction": 3083.303275,
  "actual": 3001.370949,
  "absolute_error": 81.932326,
  "source": "historical_replay"
}
```

- `source_timestamp` is the original historical observation timestamp.
- `replay_timestamp` is the wall-clock time the simulator emitted it.
- `source` is the literal string `historical_replay`.

## 7. Manifest format

A run manifest is a JSON file written under
`artifacts/v2/telemetry_replay/manifests/<run_id>.json`:

```json
{
  "run_id": "trr-20260905T035237-e636eaa4",
  "source_path": ".../artifacts/research_tables/final_predictions.csv",
  "source_sha256": "8ad40ff5aad1dcd7aff2895e7659efdef25f5069816381f6f363837b4e7dc964",
  "target": "load",
  "mode": "fast",
  "interval_seconds": 1.0,
  "limit": 5,
  "event_count": 5,
  "first_source_timestamp": "2020-11-01 00:00:00",
  "last_source_timestamp": "2020-11-01 01:00:00",
  "created_at": "2026-09-05T03:52:37.899422+00:00",
  "completed_at": "2026-09-05T03:52:38.095507+00:00",
  "artifacts_written": [
    "artifacts\\v2\\telemetry_replay\\events\\trr-20260905T035237-e636eaa4.jsonl"
  ],
  "notes": "Historical telemetry replay. Simulated event stream. Not live."
}
```

The manifest is the canonical reproducibility record. The same source
artefact + same parameters produce the same chronology, the same event
ids, and the same numeric values.

## 8. Integrity guarantees

- The source artefact is read-only. Every replay run begins with a
  SHA-256 hash of the source file; that hash is recorded in the
  manifest. The source is never written to.
- The integrity baseline (`artifacts/ui_build/phase19_integrity_baseline.json`)
  is unaffected by any replay run. A test
  (`test_no_protected_artefact_modified`) rehashes every file under
  `artifacts/research_tables/`, `artifacts/final_evaluation/`,
  `artifacts/model_registry/`, and `artifacts/mlops/` before and after a
  full replay and asserts byte-identity.
- The protocol-freeze sidecars (20 valid + 3 multi-line dataset
  manifests skipped) remain `20/20 PASS` after Stage 7.

## 9. Output location

```
artifacts/v2/
├── telemetry_replay/
│   ├── manifests/<run_id>.json
│   └── events/<run_id>.jsonl
└── experiments/    # reserved for future stages
```

The replay engine NEVER writes outside `artifacts/v2/`. The
`test_replay_writes_only_under_artifacts_v2` test enforces this.

## 10. Future integration boundary

The replay engine exposes a clean in-process iterator:

```python
engine = ReplayEngine(run)
for event in engine.events():
    consumer(event)
```

Future Stage 8 will connect this stream to incremental monitoring. The
replay foundation intentionally does NOT:

- connect to monitoring detectors,
- modify the governance policy,
- invoke retraining,
- add model serving,
- add live APIs,
- change the frontend,
- introduce LLM agents.

The integration boundary is the `events()` iterator. Anything that
implements the `TelemetryReplayEvent` consumer protocol is a valid
downstream consumer.

## 11. Failure modes

The engine fails explicitly. It never substitutes zeros, dummy
predictions, synthetic timestamps, or placeholder events.

| Failure | Behaviour |
| --- | --- |
| Source artefact missing | `FileNotFoundError` with actionable message |
| Required column missing | `ValueError` listing missing columns |
| Malformed numeric field | `ValueError` with line number |
| Unsupported target | `ValueError` listing supported targets |
| Empty dataset | `ValueError` ("contains no data rows") |
| Non-chronological source | `ReplayChronologyError` (no silent reorder) |
| Filter produces no rows | `ReplayEmptyError` |
| Paced mode with `interval <= 0` | `ValueError` |
| Unknown mode | `ValueError` listing supported modes |
| `limit <= 0` | `ValueError` |

## 12. Tests

35 tests in `tests/test_replay.py`:

- **Schema (4)**: event round-trip; event-id prefix; constants.
- **Loading (7)**: real artefact loads; missing artefact fails;
  empty data fails; missing columns fail; unsupported target fails;
  malformed number fails; target filter works.
- **Chronology (4)**: real artefact is chronological; engine
  preserves order; engine rejects non-chronological source; empty
  filter fails explicitly.
- **Replay (12)**: fast mode emits expected count; limit works;
  each target filter; no-target means all; unique event ids; paced
  mode respects interval; paced mode rejects zero interval; mode
  validation; limit validation; etc.
- **Determinism (1)**: same source → same chronology AND same
  numeric values across runs.
- **Integrity (3)**: SHA-256 recorded; source unchanged after
  replay; no protected Phase 19 artefact modified.
- **Isolation (2)**: replay writes only under `artifacts/v2/`.
- **CLI (3)**: fast+limit produces manifest + JSONL; `--no-persist`
  skips events file; missing source exits 2.

All 35 tests pass; existing 308 backend tests pass; existing 27
frontend tests pass.
