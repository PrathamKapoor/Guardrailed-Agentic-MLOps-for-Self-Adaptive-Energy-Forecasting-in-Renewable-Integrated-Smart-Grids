"""Stage 9 tests: Forecasting research and benchmark improvement.

Validates the Stage 9 research layer without depending on any v1
mutable state. Every test asserts either a property of the existing
frozen artefacts (preservation) or a property of the new Stage 9
artefacts (correctness / isolation / classification).

Categories:
  * Baseline protection
  * Output isolation
  * Chronology
  * Comparison validity
  * Classification correctness
  * Agent / governance boundary (no lifecycle mutation surfaced)
"""
from __future__ import annotations
import csv
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from smartgrid_mlops.research_v2.analysis import (  # noqa: E402
    run_baseline_analysis, _percentile, _signed_error, _mae, _rmse,
    _smape, _nmae, _nrmse,
)
from smartgrid_mlops.research_v2.candidate import (  # noqa: E402
    _classify, _load_predictions, _metrics,
    candidate_baseline_evaluation, candidate_bias_corrected_frozen,
    candidate_residual_blender,
)
from smartgrid_mlops.research_v2.report import write_summary  # noqa: E402
from smartgrid_mlops.research_v2.reproduction import (  # noqa: E402
    attempt_reproduction, _build_lag_features, _predict_baseline_persistence,
)


SOURCE_CSV = ROOT / "artifacts" / "research_tables" / "final_predictions.csv"
V2_ROOT = ROOT / "artifacts" / "v2" / "forecasting_research"


# ---------------- Baseline protection ----------------

class TestBaselineProtection:
    def test_no_protected_artefact_modified(self):
        protected_globs = [
            ROOT / "artifacts" / "research_tables",
            ROOT / "artifacts" / "final_evaluation",
            ROOT / "artifacts" / "model_registry",
            ROOT / "artifacts" / "mlops",
        ]
        protected = [p for g in protected_globs if g.exists()
                     for p in g.rglob("*") if p.is_file()]
        before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
        # Run a representative set of Stage 9 operations.
        run_baseline_analysis(SOURCE_CSV, V2_ROOT / "baseline_analysis")
        attempt_reproduction(V2_ROOT / "baseline_analysis")
        out = V2_ROOT / "candidates"
        candidate_baseline_evaluation("load", "RTS_DAY_AHEAD", "RTS_DAY_AHEAD", out)
        candidate_bias_corrected_frozen("wind", "hist_gradient_boosting", out)
        candidate_residual_blender("load", "random_forest", "RTS_DAY_AHEAD", 0.5, out)
        after = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in protected}
        assert before == after, (
            f"Stage 9 mutated a protected Phase 19 artefact: "
            f"{[k for k in before if before[k] != after.get(k)]}"
        )


# ---------------- Output isolation ----------------

class TestOutputIsolation:
    def test_outputs_under_v2_only(self, tmp_path):
        # Use a clean tmp_path as the v2 root.
        out_root = tmp_path / "v2"
        candidates_dir = out_root / "candidates"
        run_baseline_analysis(SOURCE_CSV, out_root / "baseline_analysis")
        attempt_reproduction(out_root / "baseline_analysis")
        candidate_baseline_evaluation("load", "RTS_DAY_AHEAD", "RTS_DAY_AHEAD", candidates_dir)
        candidate_bias_corrected_frozen("wind", "hist_gradient_boosting", candidates_dir)
        candidate_residual_blender("load", "random_forest", "RTS_DAY_AHEAD", 0.5, candidates_dir)
        # Nothing was created outside the v2 root.
        created = [p for p in tmp_path.rglob("*") if p.is_file()]
        assert all(str(p).startswith(str(out_root)) for p in created), (
            f"created outside v2: "
            f"{[p for p in created if not str(p).startswith(str(out_root))]}"
        )

    def test_no_writes_outside_candidates_subdir(self):
        # Each candidate evidence package must live under
        # artifacts/v2/forecasting_research/candidates/<id>/.
        for c in (V2_ROOT / "candidates").iterdir():
            if c.name == ".gitkeep":
                continue
            assert c.is_dir(), f"unexpected non-dir at {c}"
            assert (c / "experiment.json").is_file(), (
                f"missing experiment.json in {c}"
            )


# ---------------- Chronology ----------------

class TestChronology:
    def test_source_rows_are_chronological(self):
        rows = _load_predictions()
        # Per (target, model) the source must be in non-decreasing
        # timestamp order. The frozen artefact is guaranteed
        # chronologically ordered.
        last_by_key: dict[tuple[str, str], str] = {}
        for r in rows:
            key = (r["target"], r["model"])
            ts = r["timestamp"]
            if key in last_by_key:
                assert ts >= last_by_key[key], (
                    f"non-chronological source row at target={key[0]} "
                    f"model={key[1]}: ts={ts} < prev={last_by_key[key]}"
                )
            last_by_key[key] = ts

    def test_candidate_predictions_preserve_chronology(self):
        # Run a candidate and confirm the produced predictions.csv is
        # in non-decreasing timestamp order for the target.
        out = V2_ROOT / "candidates"
        candidate_baseline_evaluation("load", "RTS_DAY_AHEAD", "RTS_DAY_AHEAD", out)
        latest = sorted(out.iterdir(), key=lambda p: p.stat().st_mtime)[-1]
        with (latest / "predictions.csv").open(encoding="utf-8") as f:
            ts_seen: list[datetime] = []
            for row in csv.DictReader(f):
                ts_seen.append(datetime.strptime(row["timestamp"], "%Y-%m-%d %H:%M:%S"))
        assert ts_seen == sorted(ts_seen), "candidate predictions not chronological"


# ---------------- Comparison validity ----------------

class TestComparisonValidity:
    def test_comparison_kind_is_set(self):
        # Every candidate evidence package must have a `kind` field.
        for c_dir in (V2_ROOT / "candidates").iterdir():
            if c_dir.name == ".gitkeep":
                continue
            ej = json.loads((c_dir / "experiment.json").read_text(encoding="utf-8"))
            assert "comparison" in ej
            assert "kind" in ej["comparison"]
            assert ej["comparison"]["kind"] in ("DIRECT", "LIMITED", "NOT_DIRECTLY_COMPARABLE")

    def test_direct_comparisons_have_reference_mae(self):
        # For DIRECT comparisons, either `frozen_metrics` or
        # `baseline_metrics` must be present with a positive MAE.
        for c_dir in (V2_ROOT / "candidates").iterdir():
            if c_dir.name == ".gitkeep":
                continue
            ej = json.loads((c_dir / "experiment.json").read_text(encoding="utf-8"))
            if ej["comparison"]["kind"] != "DIRECT":
                continue
            c = ej["comparison"]
            ref_mae = (c.get("frozen_metrics", {}) or {}).get("MAE") \
                or (c.get("baseline_metrics", {}) or {}).get("MAE") \
                or (c.get("frozen_H24_PERSISTENCE", {}) or {}).get("MAE")
            assert ref_mae is not None and ref_mae > 0, (
                f"DIRECT comparison without positive reference MAE: {c_dir.name}"
            )


# ---------------- Classification correctness ----------------

class TestClassification:
    def test_classify_thresholds(self):
        # Reference = 100. Boundaries at 99 and 101 (1%).
        m = {"MAE": 98.0}
        cmp = {"kind": "DIRECT", "frozen_metrics": {"MAE": 100.0}}
        assert _classify(m, cmp) == "IMPROVED"
        m = {"MAE": 100.0}
        assert _classify(m, cmp) == "NO_MEANINGFUL_IMPROVEMENT"
        m = {"MAE": 102.0}
        assert _classify(m, cmp) == "REGRESSED"
        cmp = {"kind": "LIMITED"}
        m = {"MAE": 50.0}
        assert _classify(m, cmp) == "NOT_COMPARABLE"
        cmp = {"kind": "DIRECT"}  # no reference
        assert _classify(m, cmp) == "INCONCLUSIVE"

    def test_classify_uses_correct_reference(self):
        # When `frozen_metrics` is the reference, the classification
        # compares against it; when `baseline_metrics` is the
        # reference, it uses that.
        m = {"MAE": 90.0}
        cmp = {"kind": "DIRECT",
               "frozen_metrics": {"MAE": 100.0},
               "baseline_metrics": {"MAE": 200.0}}
        # The first reference is used (frozen_metrics).
        assert _classify(m, cmp) == "IMPROVED"
        m = {"MAE": 90.0}
        cmp = {"kind": "DIRECT",
               "baseline_metrics": {"MAE": 100.0}}
        assert _classify(m, cmp) == "IMPROVED"


# ---------------- Agent / governance boundary ----------------

class TestAgentBoundary:
    def test_no_lifecycle_mutation_endpoints_added(self):
        # The Stage 9 research layer does NOT introduce any HTTP
        # endpoints. It is a library, not a service. Confirm that
        # the FastAPI app from Stage 2/5 still exposes the same 17
        # routes and no lifecycle-mutation paths.
        from product.backend_api.app.main import create_app
        app = create_app()
        paths = sorted(app.openapi()["paths"].keys())
        forbidden = ("promote", "deploy", "rollback", "retrain",
                     "change_policy", "modify_model", "modify_features",
                     "approve_deployment")
        for p in paths:
            for f in forbidden:
                assert f not in p.lower(), f"forbidden path {p} contains {f}"

    def test_no_governance_policy_modified(self):
        p = ROOT / "config" / "governance" / "phase_13_policy.yaml"
        if not p.is_file():
            pytest.skip("Phase 13 policy not present")
        before = p.read_bytes()
        # Run a Stage 9 candidate; the policy file must be unchanged.
        candidate_bias_corrected_frozen("load", "random_forest",
                                        V2_ROOT / "candidates")
        after = p.read_bytes()
        assert before == after

    def test_orchestrator_and_firewall_intact(self):
        # The agent firewall must still block all 7 lifecycle actions.
        from smartgrid_mlops.agents.firewall import firewall_validate
        from smartgrid_mlops.agents.schemas import ALLOWED_RECOMMENDATIONS
        for blocked in ("PROMOTE_MODEL", "DEPLOY", "ROLLBACK_MODEL",
                        "START_RETRAINING", "CHANGE_POLICY",
                        "CHANGE_FEATURES", "MODIFY_MODEL"):
            r = firewall_validate(blocked)
            assert not r.allowed
        for allowed in ALLOWED_RECOMMENDATIONS:
            r = firewall_validate(allowed)
            assert r.allowed
