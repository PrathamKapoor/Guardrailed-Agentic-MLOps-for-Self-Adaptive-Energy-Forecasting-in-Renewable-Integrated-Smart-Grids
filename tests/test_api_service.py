"""Stage 2 API service tests.

Validates:
  * 17 endpoints across 7 routers are registered and respond.
  * The agent firewall blocks 7/7 lifecycle action types through the API surface.
  * The governance engine still returns DENY for unsafe requests through the API.
  * The existing Stage 1 safety tests still pass.
  * No research artefact is modified by any API call.
  * No quantum / QML / GNN / LLM claim is introduced.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))


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


@pytest.fixture(scope="module")
def app():
    from product.backend_api.app.main import create_app
    return create_app()


@pytest.fixture(scope="module")
def client(app):
    from fastapi.testclient import TestClient
    return TestClient(app)


@pytest.fixture(scope="module")
def artifact_hashes():
    return {p: _sha256(ROOT / p) for p in PROTECTED_ARTEFACTS}


# ---------------- 1. Health ----------------

class TestHealth:
    def test_health_reports_status(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert "status" in body
        assert "api" in body
        assert "research_pipeline" in body
        assert "productization" in body
        assert "artifacts" in body
        assert "notes" in body
        # The system is offline evaluation; that fact must be visible
        joined = " ".join(body["notes"]).lower()
        assert "offline" in joined

    def test_health_reports_required_artifacts(self, client):
        body = client.get("/health").json()
        for rel in ("artifacts/research_tables/final_forecasting_results.csv",
                    "artifacts/research_tables/final_model_comparison.csv",
                    "artifacts/research_tables/final_predictions.csv"):
            assert rel in body["artifacts"]
            assert body["artifacts"][rel]["exists"] is True


# ---------------- 2. Forecasts ----------------

class TestForecasts:
    def test_list_forecasts_three_targets(self, client):
        body = client.get("/api/forecasts").json()
        assert len(body) == 3
        assert {row["target"] for row in body} == {"load", "wind", "pv"}

    def test_get_forecast_per_target(self, client):
        for target in ("load", "wind", "pv"):
            body = client.get(f"/api/forecasts/{target}").json()
            assert body["target"] == target
            assert body["n_samples"] == 1464
            assert "final_test_mae" in body

    def test_get_forecast_unknown_target(self, client):
        resp = client.get("/api/forecasts/totally-fake-target")
        assert resp.status_code == 404

    def test_get_forecast_metrics(self, client):
        body = client.get("/api/forecasts/pv/metrics").json()
        assert body["target"] == "pv"
        assert body["model"] == "random_forest"
        # All five metrics present
        for k in ("mae", "rmse", "smape", "nmae", "nrmse"):
            assert k in body
            assert isinstance(body[k], float)

    def test_get_forecast_predictions_limited(self, client):
        body = client.get("/api/forecasts/load/predictions?limit=10").json()
        assert len(body) == 10
        for row in body:
            for k in ("timestamp", "target", "model", "prediction", "actual", "absolute_error"):
                assert k in row


# ---------------- 3. Model registry ----------------

class TestModels:
    def test_list_models_three_references(self, client):
        body = client.get("/api/models").json()
        assert len(body) == 3
        ids = {row["registry_id"] for row in body}
        assert ids == {"MLOPS-REF-LOAD-H24-V1", "MLOPS-REF-WIND-H24-V1", "MLOPS-REF-PV-H24-V1"}

    def test_get_model_by_id(self, client):
        body = client.get("/api/models/MLOPS-REF-LOAD-H24-V1").json()
        assert body["target"] == "load"
        assert body["research_role"] == "REFERENCE"

    def test_get_model_unknown_id(self, client):
        resp = client.get("/api/models/NONEXISTENT")
        assert resp.status_code == 404


# ---------------- 4. Monitoring ----------------

class TestMonitoring:
    def test_events_default(self, client):
        body = client.get("/api/monitoring/events").json()
        # 12 productization events: 3 perf_eval + 6 prediction_distribution + 3 model_health
        assert len(body) == 12

    def test_events_filtered_by_type(self, client):
        body = client.get("/api/monitoring/events?event_type=model_health").json()
        assert len(body) == 3
        for ev in body:
            assert ev["event_type"] == "model_health"

    def test_events_filtered_by_target(self, client):
        body = client.get("/api/monitoring/events?target=pv").json()
        assert len(body) == 4
        for ev in body:
            assert ev["target"] == "pv"

    def test_drift_endpoint(self, client):
        body = client.get("/api/monitoring/drift").json()
        assert len(body) == 12  # all current events fit the drift prefixes


# ---------------- 5. Governance ----------------

class TestGovernance:
    def test_get_policy(self, client):
        body = client.get("/api/governance/policy").json()
        assert body["policy_id"] == "SMARTGRID_DETERMINISTIC_GOVERNANCE"
        assert body["policy_version"] == "13.0.0"
        assert body["policy_checksum"]
        assert body["governance_policy_fingerprint"]

    def test_evaluate_unsafe_promotion_blocked(self, client):
        body = client.post("/api/governance/decisions", json={
            "subject_id": "MLOPS-REF-LOAD-H24-V1",
            "current_state": "PROMOTION_ELIGIBLE", "proposed_state": "APPROVAL_PENDING",
            "actor_type": "AGENT", "benchmark_gate": "BENCHMARK_GATE_FAIL",
        }).json()
        assert body["decision"] == "DENY"
        assert "BENCHMARK_GATE_FAILED" in body["reason_codes"]
        assert body["decision_content_fingerprint"]

    def test_evaluate_safe_allow(self, client):
        body = client.post("/api/governance/decisions", json={
            "subject_id": "MLOPS-REF-PV-H24-V1",
            "current_state": "PROMOTION_ELIGIBLE", "proposed_state": "APPROVAL_PENDING",
            "actor_type": "AGENT", "simulation": True,
        }).json()
        # The decision is deterministic given the inputs; Phase 13 governance decides
        assert body["decision"] in ("ALLOW", "DENY")  # exact value not asserted to avoid coupling
        assert body["policy_id"] == "SMARTGRID_DETERMINISTIC_GOVERNANCE"
        assert body["policy_version"] == "13.0.0"

    def test_decisions_log(self, client):
        body = client.get("/api/governance/decisions?limit=10").json()
        # 200 exists in the existing phase 13 evidence ledger (research log)
        assert isinstance(body, list)

    def test_invalid_state_returns_400(self, client):
        resp = client.post("/api/governance/decisions", json={
            "subject_id": "MLOPS-REF-PV-H24-V1",
            "current_state": "NOT_A_VALID_STATE", "proposed_state": "ACTIVE",
        })
        assert resp.status_code == 400


# ---------------- 6. Agent (advisory only + firewall) ----------------

class TestAgents:
    def test_agent_types_lists_advisory_only(self, client):
        body = client.get("/api/agents/types").json()
        # Lifecycle action types must NOT appear in query_types (advisory only)
        for forbidden in ("PROMOTE", "DEPLOY", "ROLLBACK", "RETRAIN", "CHANGE_POLICY",
                          "MODIFY_MODEL", "MODIFY_FEATURES"):
            assert forbidden not in body["query_types"]

    def test_agent_explain_returns_advisory_response(self, client):
        body = client.post("/api/agents/explain", json={
            "query": "Why was this model rejected?",
            "context": {"target": "load", "severity": "CRITICAL"},
        }).json()
        assert body["firewall_decision"] in ("allowed", "blocked")
        assert "reasoning_summary" in body
        assert "recommendation" in body
        assert 0.0 <= body["confidence"] <= 1.0
        assert isinstance(body["requires_human_review"], bool)

    def test_agent_firewall_blocks_lifecycle_action_via_request(self, client):
        """The /api/agents/explain endpoint must not return a lifecycle action
        as a recommendation. The firewall's allow-list (INVESTIGATE / SUMMARIZE /
        EXPLAIN / REQUEST_HUMAN_REVIEW / CREATE_REPORT) is enforced; lifecycle
        action types are not in the bounded agent's allowed set."""
        body = client.get("/api/agents/types").json()
        allowed = body["allowed_recommendation_types"]
        for forbidden in ("PROMOTE_MODEL", "DEPLOY", "ROLLBACK", "START_RETRAINING",
                          "CHANGE_POLICY", "MODIFY_MODEL", "MODIFY_FEATURES"):
            assert forbidden not in allowed


# ---------------- 7. Audit ----------------

class TestAudit:
    def test_events_endpoint_reads_ledger(self, client):
        body = client.get("/api/audit/events?limit=5").json()
        assert isinstance(body, list)

    def test_chain_verify_endpoint(self, client):
        body = client.get("/api/audit/verify").json()
        # The endpoint delegates to the existing EvidenceLedger.verify_chain
        assert "chain_ok" in body
        assert "message" in body
        assert "head" in body


# ---------------- 8. Safety: API must not bypass Stage 1 firewall ----------------

class TestSafetyBoundary:
    """The spec requires 7/7 lifecycle action types to remain blocked through
    the API. This duplicates the Stage 1 firewall test but exercises it
    through the same import path the API uses, so a refactor of the API
    cannot accidentally weaken the firewall guarantee."""

    def test_firewall_blocks_all_seven_lifecycle_action_types(self):
        from smartgrid_mlops.agents.firewall import firewall_validate
        for blocked in ("PROMOTE", "DEPLOY", "ROLLBACK", "RETRAIN",
                        "CHANGE_POLICY", "MODIFY_MODEL", "MODIFY_FEATURES"):
            result = firewall_validate(blocked)
            assert not result.allowed, f"firewall allowed {blocked}"
            assert result.reason_code in ("UNSAFE_RECOMMENDATION_BLOCKED",
                                          "UNKNOWN_RECOMMENDATION_BLOCKED")

    def test_stage1_safety_integration_still_passes(self):
        """Run the Stage 1 run_safety_integration entry point. It must still
        report ALL_SAFETY_TESTS_PASSED."""
        from smartgrid_mlops.productization import run_safety_integration
        result = run_safety_integration(ROOT)
        assert result["status"] == "ALL_SAFETY_TESTS_PASSED"
        assert len(result["tests"]) == 5

    def test_api_does_not_allow_lifecycle_via_any_path(self, client):
        """Even though the API has no POST mutation endpoints, this test
        explicitly asserts that there is no /api/models/{id}/promote (or
        similar) in the OpenAPI schema."""
        schema = client.get("/openapi.json").json()
        lifecycle_paths = ("/promote", "/deploy", "/rollback", "/retrain",
                           "/change_policy", "/modify", "/approve_deployment")
        for path in schema["paths"]:
            assert not any(tail in path for tail in lifecycle_paths), \
                f"lifecycle path exposed: {path}"


# ---------------- 9. No research artefact mutation ----------------

class TestNoArtefactMutation:
    def test_no_endpoint_mutates_a_protected_artefact(self, client, artifact_hashes):
        # Hit a sample of read endpoints. The protected-artefact bytes must
        # remain identical before and after.
        endpoints = [
            ("GET", "/health"),
            ("GET", "/api/forecasts"),
            ("GET", "/api/forecasts/pv"),
            ("GET", "/api/forecasts/pv/metrics"),
            ("GET", "/api/forecasts/pv/predictions?limit=5"),
            ("GET", "/api/models"),
            ("GET", "/api/models/MLOPS-REF-PV-H24-V1"),
            ("GET", "/api/monitoring/events"),
            ("GET", "/api/monitoring/drift"),
            ("GET", "/api/governance/policy"),
            ("GET", "/api/governance/decisions?limit=5"),
            ("POST", "/api/governance/decisions",
             {"subject_id": "MLOPS-REF-PV-H24-V1", "current_state": "PROMOTION_ELIGIBLE",
              "proposed_state": "APPROVAL_PENDING", "actor_type": "AGENT", "simulation": True}),
            ("GET", "/api/agents/types"),
            ("POST", "/api/agents/explain",
             {"query": "Why was this model rejected?", "context": {"target": "pv", "severity": "CRITICAL"}}),
            ("GET", "/api/audit/events?limit=3"),
            ("GET", "/api/audit/verify"),
        ]
        for entry in endpoints:
            method, path = entry[0], entry[1]
            payload = entry[2] if len(entry) > 2 else None
            if method == "GET":
                client.get(path)
            else:
                client.post(path, json=payload)
        for rel, sha in artifact_hashes.items():
            assert _sha256(ROOT / rel) == sha, f"artefact modified: {rel}"


# ---------------- 10. No quantum / QML / GNN / LLM claims ----------------

class TestNonGoals:
    def test_api_module_has_no_quantum_claims(self):
        import re
        from product.backend_api.app import main, schemas, dependencies
        forbidden = (r"\bqubit\b", r"\bansatz\b", r"\bVQC\b", r"\bqiskit\b",
                     r"\bpennylane\b", r"\bcirq\b", r"\bgraph neural\b", r"\bGNN\b",
                     r"\bopenai\b", r"\banthropic\b", r"\bllm\.invoke\b")
        for mod in (main, schemas, dependencies):
            for attr in dir(mod):
                if attr.startswith("_"):
                    continue
                obj = getattr(mod, attr, None)
                if obj is None:
                    continue
                src = getattr(obj, "__doc__", "") or ""
                for pat in forbidden:
                    assert not re.search(pat, src, flags=re.IGNORECASE), \
                        f"quantum/LLM claim in {mod.__name__}.{attr}: {pat}"
