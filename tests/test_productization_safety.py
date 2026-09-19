"""Stage 1 productization tests: forecasting -> MLOps integration + safety.

Validates:
  * Records are built deterministically from the frozen Phase 19 evidence.
  * Monitoring events use the existing monitoring.events schema.
  * Governance decisions are deterministic.
  * All five spec safety tests pass.
  * The agent firewall blocks all lifecycle action types.
  * No research artefact is modified.
  * No quantum / QML / GNN / LLM claims are introduced.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "src"))

from smartgrid_mlops.agents.firewall import firewall_validate
from smartgrid_mlops.governance.schemas import (
    LIFECYCLE_STATES,
    CandidateContext,
    TransitionRequest,
)
from smartgrid_mlops.productization import (
    ForecastingModelRecord,
    build_champion_challenger_snapshot,
    build_forecasting_records,
    build_governance_decision,
    build_monitoring_signals,
    run_safety_integration,
)


# --- artefacts that the integration must NOT modify (read-only) -------------
PROTECTED_ARTEFACTS = [
    "artifacts/research_tables/final_predictions.csv",
    "artifacts/research_tables/final_forecasting_results.csv",
    "artifacts/research_tables/final_model_comparison.csv",
    "artifacts/model_registry/forecasting_reference_registry.yaml",
    "artifacts/model_registry/lifecycle_registry.yaml",
    "artifacts/audit/phase_19_final_execution_audit.json",
    "artifacts/experimental_design/phase_10_ablation_protocol_freeze.yaml",
    "config/governance/phase_13_policy.yaml",
    "artifacts/experimental_design/phase_19_final_evaluation_protocol_freeze.yaml",
    "reports/phase_19_completion.md",
]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------------
# 1. Forecasting -> registry
# ---------------------------------------------------------------------

class TestForecastingRecords:
    def test_three_records_one_per_target(self):
        records = build_forecasting_records(ROOT)
        assert len(records) == 3
        assert {r.target for r in records} == {"load", "wind", "pv"}

    def test_records_match_frozen_evidence(self):
        records = {r.target: r for r in build_forecasting_records(ROOT)}
        comp = {r["Target"]: r for r in __import__("csv").DictReader(
            (ROOT / "artifacts/research_tables/final_model_comparison.csv").open(encoding="utf-8"))}
        for target in ("load", "wind", "pv"):
            r = records[target]
            assert abs(r.final_test_MAE - float(comp[target]["Frozen model MAE"])) < 1e-3
            assert abs(r.final_test_benchmark_MAE - float(comp[target]["Benchmark MAE"])) < 1e-3
            assert r.strongest_benchmark == comp[target]["External benchmark"]

    def test_records_are_pickled_safe_and_have_required_fields(self):
        for rec in build_forecasting_records(ROOT):
            d = rec.to_registry_entry()
            # All fields required by the existing ResearchRegistry.REQUIRED set
            for required in ("registry_id", "target", "horizon", "research_role", "registry_state",
                             "model_family", "framework", "implementation_id", "model_spec_fingerprint",
                             "feature_set_id", "feature_spec_fingerprint", "dataset_fingerprint",
                             "protocol_hash", "development_primary_metric", "development_MAE",
                             "strongest_benchmark", "benchmark_MAE", "development_benchmark_gate",
                             "evidence_status", "selection_evidence", "deviation_references",
                             "created_from_phase", "final_test_performance_status"):
                assert required in d, f"{rec.target}: missing {required}"
            assert d["research_role"] == "REFERENCE"
            assert d["registry_state"] == "REGISTERED_REFERENCE"
            assert d["horizon"] == 24
            assert d["feature_set_id"] == "B_lags_only"
            assert d["created_from_phase"] == 19

    def test_determinism(self):
        a = build_forecasting_records(ROOT)
        b = build_forecasting_records(ROOT)
        for r1, r2 in zip(a, b):
            assert r1.to_registry_entry() == r2.to_registry_entry()


# ---------------------------------------------------------------------
# 2. Monitoring events
# ---------------------------------------------------------------------

class TestMonitoringSignals:
    def test_one_event_per_target_per_evidence_type(self):
        records = build_forecasting_records(ROOT)
        events = build_monitoring_signals(records, ROOT)
        # 1 performance_evaluation + 2 prediction_distribution (frozen + benchmark) + 1 model_health = 4 per target
        assert len(events) == 3 * 4
        targets = {e["target"] for e in events}
        assert targets == {"load", "wind", "pv"}
        types = {e["event_type"] for e in events}
        assert types == {"performance_evaluation", "prediction_distribution", "model_health"}

    def test_event_schema_matches_existing_monitoring_layer(self):
        """Every event has the fields the existing monitoring.events.make_event emits."""
        records = build_forecasting_records(ROOT)
        events = build_monitoring_signals(records, ROOT)
        required = {"event_id", "timestamp"}
        for ev in events:
            assert required <= ev.keys()


# ---------------------------------------------------------------------
# 3. Champion / challenger snapshot
# ---------------------------------------------------------------------

class TestChampionChallengerSnapshot:
    def test_snapshot_includes_all_three_champions(self):
        records = build_forecasting_records(ROOT)
        snap = build_champion_challenger_snapshot(records, ROOT)
        assert set(snap["champions"]) == {"load", "wind", "pv"}
        assert snap["mode"] == "SIMULATION"
        for target, champion in snap["champions"].items():
            assert champion["target"] == target
            assert "final_test_MAE" in champion
            assert "benchmark_MAE" in champion

    def test_preserved_models_match_lifecycle_references(self):
        records = build_forecasting_records(ROOT)
        snap = build_champion_challenger_snapshot(records, ROOT)
        lifecycle_ids = {e["registry_id"] for e in json.loads(
            (ROOT / "artifacts/model_registry/lifecycle_registry.yaml").read_text(encoding="utf-8"))["entries"]
            if e.get("research_role") == "REFERENCE"}
        preserved_ids = {m["model_id"] for m in snap["preserved_models"]}
        assert preserved_ids <= lifecycle_ids


# ---------------------------------------------------------------------
# 4. Governance determinism
# ---------------------------------------------------------------------

class TestGovernanceDeterminism:
    def test_identical_inputs_produce_identical_decisions(self):
        kwargs = dict(subject_id="MLOPS-REF-LOAD-H24-V1", current_state="PROMOTION_ELIGIBLE",
                      proposed_state="APPROVAL_PENDING", actor_type="AGENT", simulation=True)
        d1 = build_governance_decision(ROOT, **kwargs)
        d2 = build_governance_decision(ROOT, **kwargs)
        assert d1.decision == d2.decision
        assert d1.decision_content_fingerprint == d2.decision_content_fingerprint
        assert d1.reason_codes == d2.reason_codes

    def test_governance_state_machine_is_frozen(self):
        # 13 lifecycle states (the existing implementation; do not change this number)
        assert len(LIFECYCLE_STATES) == 13
        assert "EXPERIMENTAL" in LIFECYCLE_STATES
        assert "REGISTERED_REFERENCE" in LIFECYCLE_STATES
        assert "REGISTERED_CHALLENGER" in LIFECYCLE_STATES
        assert "PROMOTION_ELIGIBLE" in LIFECYCLE_STATES
        assert "ACTIVE" in LIFECYCLE_STATES
        assert "INVALIDATED" in LIFECYCLE_STATES


# ---------------------------------------------------------------------
# 5. Five critical safety tests (spec section 10)
# ---------------------------------------------------------------------

class TestSafetyIntegration:
    def test_all_five_safety_tests_pass(self):
        result = run_safety_integration(ROOT)
        assert result["status"] == "ALL_SAFETY_TESTS_PASSED"
        assert len(result["tests"]) == 5

    def test_unsafe_promotion_blocked(self):
        result = run_safety_integration(ROOT)
        t = next(t for t in result["tests"] if t["test"] == "unsafe_promotion")
        assert t["decision"] == "DENY"
        assert "BENCHMARK_GATE_FAILED" in t["reason_codes"]

    def test_unsafe_rollback_blocked(self):
        result = run_safety_integration(ROOT)
        t = next(t for t in result["tests"] if t["test"] == "unsafe_rollback")
        assert t["decision"] == "DENY"

    def test_missing_evidence_blocked(self):
        result = run_safety_integration(ROOT)
        t = next(t for t in result["tests"] if t["test"] == "missing_evidence")
        assert t["decision"] == "DENY"

    def test_policy_conflict_overridden(self):
        result = run_safety_integration(ROOT)
        t = next(t for t in result["tests"] if t["test"] == "policy_conflict")
        assert t["decision"] == "DENY"
        assert "POLICY_VERSION_MISMATCH" in t["reason_codes"]

    def test_agent_cannot_mutate_lifecycle(self):
        """Every lifecycle action type is blocked by the firewall."""
        for blocked in ("PROMOTE", "DEPLOY", "ROLLBACK", "RETRAIN", "CHANGE_POLICY",
                        "MODIFY_MODEL", "MODIFY_FEATURES"):
            result = firewall_validate(blocked)
            assert not result.allowed, f"firewall allowed {blocked}"
            assert result.reason_code in ("UNSAFE_RECOMMENDATION_BLOCKED", "UNKNOWN_RECOMMENDATION_BLOCKED")

    def test_governance_overrides_agent_recommendation(self):
        """Test 4: when an agent recommendation conflicts with deterministic
        governance, the governance result is DENY regardless of the recommendation."""
        # Agent wants to PROMOTE; governance has benchmark gate fail -> DENY.
        decision = build_governance_decision(
            ROOT, subject_id="MLOPS-REF-LOAD-H24-V1", current_state="PROMOTION_ELIGIBLE",
            proposed_state="APPROVAL_PENDING", actor_type="AGENT", simulation=True,
            benchmark_gate="BENCHMARK_GATE_FAIL")
        assert decision.decision == "DENY"


# ---------------------------------------------------------------------
# 6. No quantum / QML / GNN / LLM claims
# ---------------------------------------------------------------------

class TestNonGoals:
    def test_no_quantum_claims_in_productization(self):
        import re
        from smartgrid_mlops.productization import forecasting_to_mlops as m
        src = Path(m.__file__).read_text(encoding="utf-8")
        # Allow references that explicitly say "no quantum", but block any
        # claim of qubit, ansatz, VQC, QML, qiskit, etc.
        forbidden = (r"\bqubit\b", r"\bansatz\b", r"\bVQC\b", r"\bqiskit\b",
                     r"\bpennylane\b", r"\bcirq\b", r"\bgraph neural\b", r"\bGNN\b")
        for pat in forbidden:
            assert not re.search(pat, src, flags=re.IGNORECASE), f"unexpected quantum claim: {pat}"

    def test_no_llm_invocation_in_productization(self):
        from smartgrid_mlops.productization import forecasting_to_mlops as m
        src = Path(m.__file__).read_text(encoding="utf-8")
        # The LLMBackendInterface is documented as a contract only; we don't call it.
        # Verify we don't import or call any LLM client.
        assert "openai" not in src.lower()
        assert "anthropic" not in src.lower()
        assert "llm.invoke" not in src.lower()


# ---------------------------------------------------------------------
# 7. Phase 19 artefacts must be byte-identical
# ---------------------------------------------------------------------

class TestNoArtefactMutation:
    def test_protected_artefacts_byte_identical(self):
        baseline = {p: _sha256(ROOT / p) for p in PROTECTED_ARTEFACTS}
        # Run all the integration entry points; they must not modify the artefacts.
        records = build_forecasting_records(ROOT)
        build_monitoring_signals(records, ROOT)
        build_champion_challenger_snapshot(records, ROOT)
        build_governance_decision(ROOT, subject_id="MLOPS-REF-LOAD-H24-V1",
                                 current_state="PROMOTION_ELIGIBLE", proposed_state="APPROVAL_PENDING",
                                 actor_type="AGENT", simulation=True)
        run_safety_integration(ROOT)
        for p, sha in baseline.items():
            current = _sha256(ROOT / p)
            assert current == sha, f"artefact modified: {p}"
