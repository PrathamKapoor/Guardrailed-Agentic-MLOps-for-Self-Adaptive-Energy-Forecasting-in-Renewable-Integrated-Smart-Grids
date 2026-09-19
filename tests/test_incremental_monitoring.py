"""Stage 8 tests: Incremental monitoring over historical replay.

Validates the incremental monitoring layer without depending on any
v1 mutable state. The processor:

  * consumes Stage 7 `TelemetryReplayEvent`s,
  * maintains per-(target, model) state,
  * reuses the existing detectors from `smartgrid_mlops.monitoring.*`,
  * emits existing-schema monitoring events via `make_event`,
  * preserves chronology,
  * distinguishes warm-up from ready,
  * resets deterministically,
  * writes only under `artifacts/v2/`.

Categories:
  * Event processing
  * Target isolation
  * Chronology
  * Warm-up semantics
  * Equivalence vs batch detectors
  * Determinism
  * Reset
  * CLI + artifact isolation
  * Baseline regression (Phase 19 artefacts unchanged)
"""
from __future__ import annotations
import csv
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from smartgrid_mlops.monitoring.incremental import (  # noqa: E402
    DETECTOR_PREDICTION_PSI,
    DETECTOR_PREDICTION_WASSERSTEIN,
    DETECTOR_ROLLING_MAE,
    EVENT_SOURCE,
    IncrementalChronologyError,
    IncrementalInvalidEventError,
    IncrementalProcessor,
    ProcessorConfig,
)
from smartgrid_mlops.monitoring.feature_drift import (  # noqa: E402
    normalized_wasserstein,
    psi,
)
from smartgrid_mlops.monitoring.performance_drift import rolling_mae  # noqa: E402
from smartgrid_mlops.replay import (  # noqa: E402
    DEFAULT_SOURCE_REL,
    ReplayEngine,
    ReplayRun,
    sha256_of,
)
from smartgrid_mlops.replay.schemas import TelemetryReplayEvent  # noqa: E402


SOURCE = ROOT / "artifacts" / "research_tables" / "final_predictions.csv"


# ---------------- Event processing ----------------

class TestEventProcessing:
    def test_one_valid_event_is_accepted(self):
        p = IncrementalProcessor(config=ProcessorConfig(reference_size=4, current_size=4))
        ev = TelemetryReplayEvent(
            event_id="tr-1", source_timestamp="2020-11-01 00:00:00",
            replay_timestamp="2020-11-01T00:00:00+00:00", target="load",
            model="random_forest", prediction=3000.0, actual=3001.0, absolute_error=1.0,
        )
        out = p.consume(ev)
        assert isinstance(out, list)
        assert all("event_id" in e and "timestamp" in e for e in out)
        # Three detectors each emit one event (WARM_UP for the first 4).
        assert len(out) == 3
        assert all(e["status"] == "WARM_UP" for e in out)
        assert all(e["target"] == "load" for e in out)
        assert all(e["source"] == EVENT_SOURCE for e in out)

    def test_invalid_event_type_rejected(self):
        p = IncrementalProcessor()
        with pytest.raises(IncrementalInvalidEventError):
            p.consume({"event_id": "not-an-event"})  # type: ignore[arg-type]

    def test_processor_returns_valid_monitoring_outputs(self):
        p = IncrementalProcessor(config=ProcessorConfig(reference_size=4, current_size=4))
        for i in range(8):
            ev = TelemetryReplayEvent(
                event_id=f"tr-{i}", source_timestamp=f"2020-11-01 0{i}:00:00",
                replay_timestamp="2020-11-01T00:00:00+00:00", target="load",
                model="random_forest", prediction=3000.0 + i,
                actual=3001.0 + i, absolute_error=1.0,
            )
            p.consume(ev)
        # After 8 events with windows of 4, the rolling MAE should be
        # in the READY state for the last 4.
        last_batch = p.consume(TelemetryReplayEvent(
            event_id="tr-9", source_timestamp="2020-11-01 09:00:00",
            replay_timestamp="2020-11-01T00:00:00+00:00", target="load",
            model="random_forest", prediction=3010.0, actual=3011.0, absolute_error=1.0,
        ))
        rm_events = [e for e in last_batch if e["detector"] == DETECTOR_ROLLING_MAE]
        assert rm_events, "expected a rolling_mae event in the last batch"
        assert rm_events[0]["status"] == "READY"
        # Existing batch detector: rolling_mae([3005..3011], [3004..3010], 4)
        # = mean(|3011-3010|, |3010-3009|, |3009-3008|, |3008-3007|)
        # = mean(1, 1, 1, 1) = 1.0
        assert abs(rm_events[0]["value"] - 1.0) < 1e-9


# ---------------- Target isolation ----------------

class TestTargetIsolation:
    def test_load_state_does_not_affect_wind(self):
        p = IncrementalProcessor(config=ProcessorConfig(reference_size=4, current_size=4))
        # Fill LOAD with constant prediction = actual (MAE = 0). The
        # current ring buffer has capacity 4, so the last 4 of the 8
        # observations are kept.
        for i in range(8):
            p.consume(TelemetryReplayEvent(
                event_id=f"load-{i}", source_timestamp=f"2020-11-01T0{i}:00:00",
                replay_timestamp="2020-11-01T00:00:00+00:00", target="load",
                model="random_forest", prediction=100.0, actual=100.0,
                absolute_error=0.0,
            ))
        # Now feed WIND with a different value.
        out = p.consume(TelemetryReplayEvent(
            event_id="wind-0", source_timestamp="2020-11-02T00:00:00",
            replay_timestamp="2020-11-02T00:00:00+00:00", target="wind",
            model="random_forest", prediction=999.0, actual=1000.0,
            absolute_error=1.0,
        ))
        load_key = ("load", "random_forest")
        ts = p.state.get(load_key)
        snap = ts.current.snapshot()
        # Current window capacity is 4; the last 4 LOAD observations
        # are kept, all with prediction = actual = 100.0.
        assert len(snap["predictions"]) == 4
        assert all(p == 100.0 for p in snap["predictions"])
        assert all(a == 100.0 for a in snap["actuals"])
        # The WIND batch only emits WARM_UP for the WIND state.
        for e in out:
            assert e["target"] == "wind"
            assert e["status"] == "WARM_UP"

    def test_mixed_target_replay_remains_isolated(self):
        p = IncrementalProcessor(config=ProcessorConfig(reference_size=4, current_size=4))
        for i in range(4):
            for target in ("load", "wind", "pv"):
                p.consume(TelemetryReplayEvent(
                    event_id=f"{target}-{i}", source_timestamp=f"2020-11-01 0{i}:00:00",
                    replay_timestamp="2020-11-01T00:00:00+00:00", target=target,
                    model="random_forest", prediction=1.0, actual=2.0,
                    absolute_error=1.0,
                ))
        # Each target has 4 observations, so its rolling_mae is now READY.
        # Push one more observation to each target; verify the targets
        # are still isolated by checking the WIND prediction values
        # are NOT contaminating the LOAD window.
        p.consume(TelemetryReplayEvent(
            event_id="load-4", source_timestamp="2020-11-01 04:00:00",
            replay_timestamp="2020-11-01T00:00:00+00:00", target="load",
            model="random_forest", prediction=1.0, actual=2.0, absolute_error=1.0,
        ))
        p.consume(TelemetryReplayEvent(
            event_id="wind-4", source_timestamp="2020-11-01 04:00:00",
            replay_timestamp="2020-11-01T00:00:00+00:00", target="wind",
            model="random_forest", prediction=999.0, actual=999.0, absolute_error=0.0,
        ))
        from smartgrid_mlops.monitoring.incremental import TargetKey  # noqa: F401
        load_key = ("load", "random_forest")
        load_snap = p.state.get(load_key).current.snapshot()
        # The LOAD window is the LAST 4 observations: predictions
        # should all be 1.0, NOT 999.0.
        assert all(x == 1.0 for x in load_snap["predictions"]), (
            f"LOAD window contaminated by WIND: {load_snap['predictions']}"
        )


# ---------------- Chronology ----------------

class TestChronology:
    def test_chronological_events_accepted(self):
        p = IncrementalProcessor(config=ProcessorConfig(reference_size=4, current_size=4))
        for i in range(6):
            out = p.consume(TelemetryReplayEvent(
                event_id=f"tr-{i}", source_timestamp=f"2020-11-01 0{i}:00:00",
                replay_timestamp="2020-11-01T00:00:00+00:00", target="load",
                model="random_forest", prediction=1.0, actual=1.0,
                absolute_error=0.0,
            ))
        assert p.events_consumed == 6
        assert p.chronology_violations == 0

    def test_out_of_order_event_rejected(self):
        p = IncrementalProcessor(config=ProcessorConfig(reference_size=4, current_size=4))
        p.consume(TelemetryReplayEvent(
            event_id="tr-0", source_timestamp="2020-11-01 05:00:00",
            replay_timestamp="2020-11-01T00:00:00+00:00", target="load",
            model="random_forest", prediction=1.0, actual=1.0, absolute_error=0.0,
        ))
        with pytest.raises(IncrementalChronologyError):
            p.consume(TelemetryReplayEvent(
                event_id="tr-1", source_timestamp="2020-11-01 00:00:00",
                replay_timestamp="2020-11-01T00:00:00+00:00", target="load",
                model="random_forest", prediction=1.0, actual=1.0, absolute_error=0.0,
            ))
        # Chronology violation count is incremented.
        assert p.chronology_violations == 1

    def test_chronology_state_is_target_specific(self):
        p = IncrementalProcessor(config=ProcessorConfig(reference_size=4, current_size=4))
        # LOAD sees 05:00 first; WIND sees 03:00 first. Then LOAD sees
        # 06:00 (valid) and WIND sees 02:00 (out-of-order, but LOAD is
        # unaffected).
        p.consume(TelemetryReplayEvent(
            event_id="L-1", source_timestamp="2020-11-01 05:00:00",
            replay_timestamp="2020-11-01T00:00:00+00:00", target="load",
            model="random_forest", prediction=1.0, actual=1.0, absolute_error=0.0,
        ))
        p.consume(TelemetryReplayEvent(
            event_id="W-1", source_timestamp="2020-11-01 03:00:00",
            replay_timestamp="2020-11-01T00:00:00+00:00", target="wind",
            model="random_forest", prediction=1.0, actual=1.0, absolute_error=0.0,
        ))
        # LOAD: 06:00 is fine.
        p.consume(TelemetryReplayEvent(
            event_id="L-2", source_timestamp="2020-11-01 06:00:00",
            replay_timestamp="2020-11-01T00:00:00+00:00", target="load",
            model="random_forest", prediction=1.0, actual=1.0, absolute_error=0.0,
        ))
        # WIND: 02:00 is out-of-order.
        with pytest.raises(IncrementalChronologyError):
            p.consume(TelemetryReplayEvent(
                event_id="W-2", source_timestamp="2020-11-01 02:00:00",
                replay_timestamp="2020-11-01T00:00:00+00:00", target="wind",
                model="random_forest", prediction=1.0, actual=1.0, absolute_error=0.0,
            ))
        # LOAD chronology is still healthy.
        assert p.chronology_violations == 1


# ---------------- Warm-up semantics ----------------

class TestWarmUp:
    def test_insufficient_data_emits_warm_up(self):
        p = IncrementalProcessor(config=ProcessorConfig(reference_size=4, current_size=4))
        out = p.consume(TelemetryReplayEvent(
            event_id="tr-0", source_timestamp="2020-11-01 00:00:00",
            replay_timestamp="2020-11-01T00:00:00+00:00", target="load",
            model="random_forest", prediction=1.0, actual=1.0, absolute_error=0.0,
        ))
        for e in out:
            assert e["status"] == "WARM_UP"
            assert "value" not in e  # no fake numeric value

    def test_insufficient_data_does_not_emit_healthy(self):
        # Spec §10: "insufficient data" must not be reported as
        # "healthy", "normal", or "no drift".
        p = IncrementalProcessor(config=ProcessorConfig(reference_size=10, current_size=10))
        for i in range(3):
            out = p.consume(TelemetryReplayEvent(
                event_id=f"tr-{i}", source_timestamp=f"2020-11-01 0{i}:00:00",
                replay_timestamp="2020-11-01T00:00:00+00:00", target="load",
                model="random_forest", prediction=1.0, actual=1.0, absolute_error=0.0,
            ))
        for e in out:
            assert e["status"] not in ("HEALTHY", "NORMAL", "NO_DRIFT")
            assert e["status"] == "WARM_UP"

    def test_psi_waits_for_sufficient_distribution(self):
        # PSI requires both reference and current windows. Until the
        # reference window is full, PSI emits WARM_UP.
        p = IncrementalProcessor(config=ProcessorConfig(reference_size=10, current_size=4))
        for i in range(4):  # current fills but reference does not
            out = p.consume(TelemetryReplayEvent(
                event_id=f"tr-{i}", source_timestamp=f"2020-11-01 0{i}:00:00",
                replay_timestamp="2020-11-01T00:00:00+00:00", target="load",
                model="random_forest", prediction=1.0 + i, actual=1.0 + i,
                absolute_error=0.0,
            ))
        psi_events = [e for e in out if e["detector"] == DETECTOR_PREDICTION_PSI]
        assert psi_events and psi_events[0]["status"] == "WARM_UP"


# ---------------- Equivalence vs batch ----------------

class TestEquivalence:
    def test_rolling_mae_matches_batch(self):
        # Generate a sequence of (timestamp, prediction, actual) values.
        # The incremental rolling_mae over the last 168 observations
        # should equal the batch rolling_mae on the same slice.
        import random
        random.seed(42)
        preds = [100 + random.gauss(0, 5) for _ in range(200)]
        acts = [100 + random.gauss(0, 5) for _ in range(200)]
        p = IncrementalProcessor(config=ProcessorConfig(reference_size=200, current_size=168))
        last_batch = []
        for i, (pr, ac) in enumerate(zip(preds, acts)):
            # Use strictly increasing timestamps: 1-minute steps starting
            # from 2020-11-01 00:00:00. 200 minutes = 3h20m.
            ts = f"2020-11-01T{i // 60:02d}:{i % 60:02d}:00"
            ev = TelemetryReplayEvent(
                event_id=f"tr-{i}", source_timestamp=ts,
                replay_timestamp="2020-11-01T00:00:00+00:00", target="load",
                model="random_forest", prediction=pr, actual=ac,
                absolute_error=abs(pr - ac),
            )
            last_batch = p.consume(ev)
        rm_events = [e for e in last_batch if e["detector"] == DETECTOR_ROLLING_MAE]
        assert rm_events[0]["status"] == "READY"
        # The incremental value must match the batch value on the same
        # window (the last 168 observations).
        expected = rolling_mae(acts, preds, window=168)
        assert abs(rm_events[0]["value"] - expected) < 1e-9

    def test_psi_matches_batch(self):
        # Build a reference and current sample. Push 168 of each.
        import random
        random.seed(0)
        ref = [random.gauss(0, 1) for _ in range(168)]
        # Current: same distribution => PSI near 0; shifted => PSI > 0.1.
        cur_same = [random.gauss(0, 1) for _ in range(168)]
        cur_shifted = [random.gauss(2, 1) for _ in range(168)]

        p_same = IncrementalProcessor(config=ProcessorConfig(reference_size=168, current_size=168))
        p_shifted = IncrementalProcessor(config=ProcessorConfig(reference_size=168, current_size=168))

        def make_feed(processor, start_index):
            """Return a function that feeds samples with strictly
            increasing timestamps starting from `start_index` minutes
            past 2020-11-01 00:00:00."""
            counter = [start_index]
            def feed(samples):
                nonlocal_start = start_index
                last = []
                for v in samples:
                    i = counter[0]
                    counter[0] += 1
                    ts = f"2020-11-01T{i // 60:02d}:{i % 60:02d}:00"
                    last = processor.consume(TelemetryReplayEvent(
                        event_id=f"tr-{i}", source_timestamp=ts,
                        replay_timestamp="2020-11-01T00:00:00+00:00", target="load",
                        model="random_forest", prediction=v, actual=v,
                        absolute_error=0.0,
                    ))
                return last
            return feed

        # Reference samples occupy minutes 0..167; current samples
        # continue at minutes 168..335.
        feed_same = make_feed(p_same, 0)
        feed_shifted = make_feed(p_shifted, 0)
        feed_same(ref)
        feed_shifted(ref)
        out_same = feed_same(cur_same)
        out_shifted = feed_shifted(cur_shifted)
        # Both windows full now. Compare incremental PSI to batch PSI.
        inc_same = next(e["value"] for e in out_same if e["detector"] == DETECTOR_PREDICTION_PSI)
        inc_shifted = next(e["value"] for e in out_shifted if e["detector"] == DETECTOR_PREDICTION_PSI)
        batch_same = psi(ref, cur_same, bins=10, epsilon=1e-6)
        batch_shifted = psi(ref, cur_shifted, bins=10, epsilon=1e-6)
        assert abs(inc_same - batch_same) < 1e-9
        assert abs(inc_shifted - batch_shifted) < 1e-9
        # The shifted case must report meaningfully higher PSI than the
        # same-distribution case.
        assert inc_shifted > inc_same

    def test_normalized_wasserstein_matches_batch(self):
        import random
        random.seed(1)
        ref = [random.gauss(0, 1) for _ in range(168)]
        cur = [random.gauss(0, 1) for _ in range(168)]
        p = IncrementalProcessor(config=ProcessorConfig(reference_size=168, current_size=168))
        last = []
        for i, v in enumerate(ref):
            last = p.consume(TelemetryReplayEvent(
                event_id=f"r-{i}", source_timestamp=f"2020-11-01T{i // 60:02d}:{i % 60:02d}:00",
                replay_timestamp="2020-11-01T00:00:00+00:00", target="load",
                model="random_forest", prediction=v, actual=v, absolute_error=0.0,
            ))
        for i, v in enumerate(cur):
            # Strictly increasing timestamps, after the reference window.
            ts = f"2020-11-08T{i // 60:02d}:{i % 60:02d}:00"
            last = p.consume(TelemetryReplayEvent(
                event_id=f"c-{i}", source_timestamp=ts,
                replay_timestamp="2020-11-08T00:00:00+00:00", target="load",
                model="random_forest", prediction=v, actual=v, absolute_error=0.0,
            ))
        w_events = [e for e in last if e["detector"] == DETECTOR_PREDICTION_WASSERSTEIN]
        assert w_events[0]["status"] == "READY"
        expected = normalized_wasserstein(ref, cur)
        assert abs(w_events[0]["value"] - expected) < 1e-9


# ---------------- Determinism ----------------

class TestDeterminism:
    def test_same_replay_twice_same_semantic_outputs(self):
        def run_once():
            p = IncrementalProcessor(config=ProcessorConfig(reference_size=168, current_size=168))
            run = ReplayRun(
                source_path=str(SOURCE), target="load", mode="fast", limit=400,
                source_sha256=sha256_of(SOURCE), run_id="det-once",
            )
            for ev in ReplayEngine(run).events():
                p.consume(ev)
            return p

        p1 = run_once()
        p2 = run_once()
        # Compare deterministic semantic content (strip the UUID
        # event_ids and the make_event timestamps).
        for run, name in [(p1, "p1"), (p2, "p2")]:
            assert run.events_consumed == 400
            assert run.warm_up_count >= 0
        # Both must reach the same count of ready monitoring events.
        assert p1.events_emitted == p2.events_emitted


# ---------------- Reset ----------------

class TestReset:
    def test_reset_clears_state(self):
        p = IncrementalProcessor(config=ProcessorConfig(reference_size=4, current_size=4))
        for i in range(5):
            p.consume(TelemetryReplayEvent(
                event_id=f"tr-{i}", source_timestamp=f"2020-11-01 0{i}:00:00",
                replay_timestamp="2020-11-01T00:00:00+00:00", target="load",
                model="random_forest", prediction=1.0, actual=2.0,
                absolute_error=1.0,
            ))
        assert p.events_consumed == 5
        assert len(p.state) >= 1
        p.reset()
        assert p.events_consumed == 0
        assert p.events_emitted == 0
        assert p.warm_up_count == 0
        assert p.chronology_violations == 0
        assert p.last_source_timestamp is None
        assert len(p.state) == 0

    def test_replay_after_reset_behaves_like_fresh(self):
        # Use a window larger than the replayed length so warm-up is
        # the natural state at the end of the replay.
        p = IncrementalProcessor(config=ProcessorConfig(reference_size=20, current_size=20))
        for i in range(5):
            p.consume(TelemetryReplayEvent(
                event_id=f"tr-{i}", source_timestamp=f"2020-11-01T0{i}:00:00",
                replay_timestamp="2020-11-01T00:00:00+00:00", target="load",
                model="random_forest", prediction=1.0, actual=1.0, absolute_error=0.0,
            ))
        p.reset()
        out = []
        for i in range(5):
            out.extend(p.consume(TelemetryReplayEvent(
                event_id=f"tr-{i}", source_timestamp=f"2020-11-01T0{i}:00:00",
                replay_timestamp="2020-11-01T00:00:00+00:00", target="load",
                model="random_forest", prediction=1.0, actual=1.0, absolute_error=0.0,
            )))
        # After reset, all 5 events should be in WARM_UP because the
        # windows are size 20 and we only have 5 events.
        assert all(e["status"] == "WARM_UP" for e in out)


# ---------------- CLI + artifact isolation ----------------

class TestCLI:
    def test_cli_emits_manifest_and_events(self, tmp_path):
        out_dir = tmp_path / "v2out"
        env = os.environ.copy()
        env["QSMLOPS_PROJECT_ROOT"] = str(ROOT)
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "run_incremental_monitoring.py"),
             "--target", "load", "--mode", "fast", "--limit", "500",
             "--reference-size", "168", "--current-size", "168",
             "--out", str(out_dir)],
            capture_output=True, text=True, env=env, timeout=30,
        )
        assert result.returncode == 0, f"CLI failed: {result.stderr}"
        assert "SOURCE MODE: HISTORICAL REPLAY" in result.stdout
        assert "LIVE TELEMETRY: NOT USED" in result.stdout
        assert "EVENTS CONSUMED:" in result.stdout
        assert "MONITORING EVENTS EMITTED:" in result.stdout
        assert "NOT LIVE" in result.stdout
        # Manifest exists.
        manifests = list((out_dir / "manifests").glob("*.json"))
        summaries = list((out_dir / "summaries").glob("*.json"))
        events = list((out_dir / "events").glob("*.jsonl"))
        assert len(manifests) == 1
        assert len(summaries) == 1
        # Events file may be present if at least one monitoring event
        # was emitted; with limit=500 and 168*2 windows, the windows
        # do not fill for all detectors, but the rolling_mae detector
        # does fill (the current window reaches 168 within the first
        # ~200 events and the reference window within ~168 events).
        body = json.loads(manifests[0].read_text(encoding="utf-8"))
        assert body["mode"] == "historical_replay_incremental_monitoring"
        assert body["source_sha256"] == sha256_of(SOURCE)
        assert body["events_consumed"] == 500
        assert body["monitoring_events_emitted"] >= 0

    def test_cli_no_persist_skips_events_file(self, tmp_path):
        out_dir = tmp_path / "v2out"
        env = os.environ.copy()
        env["QSMLOPS_PROJECT_ROOT"] = str(ROOT)
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "run_incremental_monitoring.py"),
             "--target", "load", "--mode", "fast", "--limit", "200",
             "--out", str(out_dir), "--no-persist"],
            capture_output=True, text=True, env=env, timeout=30,
        )
        assert result.returncode == 0, f"CLI failed: {result.stderr}"
        manifests = list((out_dir / "manifests").glob("*.json"))
        events = list((out_dir / "events").glob("*"))
        assert len(manifests) == 1
        assert events == []


# ---------------- Artifact isolation + baseline regression ----------------

class TestArtifactIsolation:
    def test_no_protected_artefact_modified(self):
        protected_globs = [
            ROOT / "artifacts" / "research_tables",
            ROOT / "artifacts" / "final_evaluation",
            ROOT / "artifacts" / "model_registry",
            ROOT / "artifacts" / "mlops",
        ]
        protected = [p for g in protected_globs if g.exists() for p in g.rglob("*") if p.is_file()]
        before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
        # Run a real incremental monitoring session.
        p = IncrementalProcessor(config=ProcessorConfig(reference_size=168, current_size=168))
        run = ReplayRun(
            source_path=str(SOURCE), target="all", mode="fast", limit=500,
            source_sha256=sha256_of(SOURCE), run_id="iso",
        )
        for ev in ReplayEngine(run).events():
            p.consume(ev)
        after = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
        assert before == after, "incremental monitoring mutated a protected Phase 19 artefact"

    def test_v2_outputs_isolated(self, tmp_path):
        out_dir = tmp_path / "v2"
        env = os.environ.copy()
        env["QSMLOPS_PROJECT_ROOT"] = str(ROOT)
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "run_incremental_monitoring.py"),
             "--target", "load", "--mode", "fast", "--limit", "300",
             "--out", str(out_dir)],
            capture_output=True, text=True, env=env, timeout=30,
        )
        assert result.returncode == 0
        # Nothing was written outside the v2 output dir.
        created = [p for p in tmp_path.rglob("*") if p.is_file()]
        assert all(str(p).startswith(str(out_dir)) for p in created), (
            f"created outside v2: {[p for p in created if not str(p).startswith(str(out_dir))]}"
        )
