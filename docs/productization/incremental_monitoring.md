# Incremental Monitoring over Historical Replay (Stage 8)

## 1. Purpose

The Stage 8 incremental monitoring layer consumes Stage 7
`TelemetryReplayEvent`s one at a time and produces existing-schema
monitoring events using the detectors already exported by
`smartgrid_mlops.monitoring.*`. It is a stateful adapter that lets
the repository's existing batch monitoring logic be exercised
incrementally against replayed observations.

> Incremental monitoring processes historical observations as they
> are replayed event-by-event. It simulates streaming-style processing
> but does not monitor a live energy system.

## 2. Relationship to Stage 7

```
Stage 7 (Historical Telemetry Replay)
    │
    │ one chronological event
    ▼
Stage 8 (Incremental Monitoring)
    │
    ├── rolling performance monitoring
    ├── prediction PSI
    └── prediction normalized_wasserstein
    │
    ▼
Existing Monitoring Event Schema
    │
    ▼
Future Stage 9+
```

Stage 8 takes the Stage 7 `TelemetryReplayEvent` stream as input.
The Stage 7 contract is reused as-is: event_id, source_timestamp,
target, model, prediction, actual, absolute_error. No duplicate
schema was created.

## 3. Incremental processing architecture

```
Replay Event
    │
    ▼
IncrementalProcessor.consume(event)
    │
    ├── validate event
    ├── enforce chronology (per target × model)
    ├── update per-target state (ring buffers)
    │
    ├── detector: rolling_mae  (existing)
    │       └─ monitor: current window ≥ reference size
    │
    ├── detector: prediction_psi  (existing)
    │       └─ monitor: BOTH reference and current windows full
    │
    └── detector: prediction_wasserstein  (existing)
            └─ monitor: BOTH reference and current windows full
    │
    ▼
make_event(...)            (existing)
    │
    ▼
[ event_id, timestamp, target, model, status, value, source, ... ]
```

## 4. Target-specific state

State is keyed on `(target, model)`. Each key has:

- A reference ring buffer of size `reference_size` (default 168).
- A current ring buffer of size `current_size` (default 168).
- The last observed `source_timestamp` (for chronology enforcement).

A LOAD observation never enters a WIND window. A `random_forest`
observation never enters a `mlp` window. The processor holds separate
`TargetState` instances per key.

## 5. Warm-up behaviour

A detector emits a result with `status="WARM_UP"` when its window
is not yet at capacity. During warm-up:

- The result carries NO numeric value (no fake numbers).
- The status is the literal string `WARM_UP`, never `HEALTHY`,
  `NORMAL`, or `NO_DRIFT`.
- The result includes `observations` and `window` fields so the
  consumer knows the warm-up state.

A detector emits `status="READY"` only when its window has at least
`min_window_fraction * capacity` observations AND `capacity` observations
total.

## 6. Detectors reused

The incremental layer does NOT introduce new monitoring math. It
reuses:

| Detector | Source | Used for |
| --- | --- | --- |
| `rolling_mae` | `monitoring.performance_drift` | rolling performance over current window |
| `psi` | `monitoring.feature_drift` | prediction-distribution PSI |
| `normalized_wasserstein` | `monitoring.feature_drift` | prediction-distribution drift |
| `prediction_signal` | `monitoring.prediction_drift` | (available; underlying primitive is reused directly) |
| `make_event` | `monitoring.events` | monitoring event creation |
| `classify_severity` | `monitoring.severity` | (available; severity is exposed in the event payload) |

### KS detector — explicit gap

The Stage 7 spec requested reuse of an "existing KS detector". A
grep of `src/` for `ks_2samp`, `ks_test`, `kolmogorov`,
`scipy.stats.kstest`, etc. returns zero hits. **No Kolmogorov-Smirnov
implementation exists in the repository's monitoring layer.** The
honest decision is to document this gap and not invent a new KS
detector in this stage. The existing PSI and Wasserstein detectors
provide distribution-drift coverage; KS would be additive and is left
to a future stage that explicitly adds it to the existing monitoring
package.

## 7. Existing metrics reused

The incremental layer emits values that are **numerically equal** to
the existing batch implementations. The test suite
`tests/test_incremental_monitoring.py` asserts this:

- `test_rolling_mae_matches_batch` — incremental rolling MAE on the
  last N observations equals batch `rolling_mae(y, pred, window=N)`.
- `test_psi_matches_batch` — incremental PSI on the reference and
  current windows equals batch `psi(reference, current, bins=10, epsilon=1e-6)`.
- `test_normalized_wasserstein_matches_batch` — incremental
  normalized_wasserstein equals the batch implementation.

## 8. Event schema reused

Every event is created via `monitoring.events.make_event(**kwargs)`,
the same function the productization layer in
`forecasting_to_mlops.py` already uses. The output event includes:

- `event_id` (UUIDv4 from `make_event`),
- `timestamp` (wall-clock from `make_event`),
- `detector`, `target`, `model`, `status` (READY or WARM_UP),
- `value` (numeric, only when READY),
- `source` (the literal `historical_replay_incremental_monitoring`),
- plus per-detector fields (`window`, `observations`,
  `reference_observations`, `current_observations`, `bins`, `unit`).

A second event schema was NOT introduced.

## 9. CLI usage

```bash
.venv\Scripts\python.exe scripts/run_incremental_monitoring.py --target load --mode fast --limit 1000
.venv\Scripts\python.exe scripts/run_incremental_monitoring.py --target all --mode paced --interval 0.1
.venv\Scripts\python.exe scripts/run_incremental_monitoring.py --target pv --mode fast --no-persist
```

The CLI prints:

```
SOURCE MODE: HISTORICAL REPLAY
LIVE TELEMETRY: NOT USED
  source_path:    ...
  source_sha256:  ...
  target:         load
  mode:           fast
  limit:          1000
  reference_size: 168
  current_size:   168
  run_id:         imr-...
  out_dir:        artifacts/v2/incremental_monitoring
  ...

EVENTS CONSUMED: 1000
MONITORING EVENTS EMITTED: ...
WARM-UP DETECTOR EVALUATIONS: ...
  manifest: artifacts/v2/incremental_monitoring/manifests/...json
  summary:  artifacts/v2/incremental_monitoring/summaries/...json
  events:   artifacts/v2/incremental_monitoring/events/...jsonl
NOTE: HISTORICAL REPLAY + INCREMENTAL MONITORING. NOT LIVE.
```

## 10. Output locations

```
artifacts/v2/
└── incremental_monitoring/
    ├── manifests/<run_id>.json   # run parameters, counts, source SHA-256
    ├── summaries/<run_id>.json   # same content as the manifest (for fast grep)
    └── events/<run_id>.jsonl    # one monitoring event per line
```

Nothing is written outside `artifacts/v2/`. The CLI's `--out` flag can
redirect to any path; the isolation test asserts that no file is
created outside the requested directory.

## 11. Determinism guarantees

The processor is a pure function of the input event sequence. Two
runs of the same replay produce the same number of monitoring events,
the same numeric values, and the same status flags. The existing
`make_event` uses UUIDv4 for `event_id` and `datetime.now()` for
`timestamp` — both contain non-deterministic metadata. Tests therefore
compare semantic content (detector name, target, model, status,
value) rather than raw event ids.

## 12. Explicit distinction from live monitoring

The Stage 8 layer is **incremental monitoring over historical
replay**. It is NOT:

- live smart-grid monitoring,
- real-time grid monitoring,
- streaming production infrastructure,
- online drift detection on live data.

The literal string `historical_replay_incremental_monitoring` is the
`source` field of every emitted monitoring event. The CLI prints
`LIVE TELEMETRY: NOT USED` on every run. The manifest and summary
files carry `mode: "historical_replay_incremental_monitoring"`.

## 13. Tests

21 tests in `tests/test_incremental_monitoring.py`:

- **Event processing** (3): valid event accepted; invalid event
  rejected; processor returns valid monitoring outputs.
- **Target isolation** (2): LOAD state does not affect WIND; mixed
  target replay remains isolated.
- **Chronology** (3): chronological events accepted; out-of-order
  events rejected; chronology state is target-specific.
- **Warm-up** (3): insufficient data emits WARM_UP; insufficient
  data does not emit HEALTHY/NO_DRIFT; PSI waits for distribution
  data.
- **Equivalence vs batch** (3): rolling MAE matches batch; PSI
  matches batch (and shifted > same); Wasserstein matches batch.
- **Determinism** (1): same replay twice → same semantic outputs.
- **Reset** (2): reset clears state; replay after reset behaves
  like fresh.
- **CLI** (2): emits manifest + events; `--no-persist` skips events.
- **Artifact isolation** (2): no protected artefact modified; v2
  outputs isolated.

All 21 pass. Existing 308 backend tests + 35 Stage 7 replay tests
continue to pass (343+21=364 expected after this stage).
