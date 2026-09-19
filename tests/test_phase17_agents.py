from __future__ import annotations
import json
from pathlib import Path

import pytest

from smartgrid_mlops.agents.audit import emit as agent_emit, read_agent_events
from smartgrid_mlops.agents.base import LLMBackendInterface, LocalRuleBackend
from smartgrid_mlops.agents.drift_agent import DriftAnalysisAgent
from smartgrid_mlops.agents.evidence_agent import EvidenceRetrievalAgent
from smartgrid_mlops.agents.firewall import firewall_validate
from smartgrid_mlops.agents.governance_agent import GovernanceExplanationAgent
from smartgrid_mlops.agents.memory import MemoryStore
from smartgrid_mlops.agents.orchestrator import Orchestrator
from smartgrid_mlops.agents.planner import Planner
from smartgrid_mlops.agents.retraining_agent import RetrainingExplanationAgent
from smartgrid_mlops.agents.report_agent import ReportGenerationAgent
from smartgrid_mlops.agents.schemas import (ALLOWED_RECOMMENDATIONS, AgentQuery, BLOCKED_RECOMMENDATIONS,
                                            MEMORY_FIELDS, OUTPUT_CONTRACT_FIELDS)
from smartgrid_mlops.agents.validation import (assert_no_final_test_access, assert_no_forbidden_agent_events,
                                               assert_structured_evidence, assert_valid_output)

ROOT = Path(__file__).parents[1]


@pytest.fixture()
def orchestrator(tmp_path):
    return Orchestrator(ROOT, audit_path=tmp_path / "audit.jsonl", memory_dir=tmp_path / "memory")


DRIFT_EVENT = {"event_id": "e1", "target": "load", "scenario_id": "A15-01-HIGH-load", "severity": "CRITICAL",
               "triggered": ["FEATURE_DRIFT", "PERFORMANCE_DRIFT"],
               "signal_values": {"feature_stat": 1.2, "prediction_stat": 0.4, "performance_stat": 0.9}}
RETRAIN_DENY = {"decision": "DENY", "target": "load", "reason_codes": ["DATA_QUALITY_BLOCK"],
                "gate_results": [{"gate": "DATA_QUALITY_GATE", "passed": False}], "policy_version": "15.0.0",
                "simulation_scenario_id": None}
RETRAIN_ALLOW = {"decision": "ALLOW", "target": "pv", "reason_codes": ["RETRAINING_ALLOWED"],
                 "gate_results": [{"gate": "g", "passed": True}], "policy_version": "15.0.0",
                 "simulation_scenario_id": "A15-01-LOW-pv"}
PROMOTION_REJECT = {"decision": "REJECT", "challenger_id": "CHAL", "reference_id": "REF", "target": "load",
                    "reason_codes": ["BENCHMARK_REQUIREMENT_NOT_SATISFIED"],
                    "gate_results": [{"gate": "BENCHMARK_GATE", "passed": False}],
                    "metrics": {"reference_mae": 100.0, "challenger_mae": 90.0, "matched_evaluation_rows": 336}}
ROLLBACK = {"outcome": "ROLLBACK_COMPLETED", "promoted_model_id": "CHAL", "previous_model_id": "REF",
            "degradation_percent": 4.2, "threshold_percent": 0.0,
            "verification": {"checks": {"artifact_exists": True, "fingerprint_matches": True,
                                        "lineage_exists": True, "model_loads": True, "outputs_finite": True}}}


def test_agent_can_explain_drift(orchestrator):
    result = orchestrator.handle(AgentQuery("EXPLAIN_DRIFT", {"drift_event": DRIFT_EVENT, "evidence_refs": ["e.jsonl"]}))
    output = result["output"]
    assert output["agent_id"] == "DRIFT_ANALYSIS_AGENT" and output["recommendation"] == "INVESTIGATE"
    assert output["requires_human_review"] and not output["blocked"]
    assert "CRITICAL" in output["reasoning_summary"] and "load" in output["reasoning_summary"]
    assert "FEATURE_DRIFT" in output["reasoning_summary"] and "Possible causes" in output["reasoning_summary"]


def test_agent_can_explain_retraining_decision(orchestrator):
    denied = orchestrator.handle(AgentQuery("EXPLAIN_RETRAINING", {"retraining_decision": RETRAIN_DENY}))
    assert "denied" in denied["output"]["reasoning_summary"]
    assert "DATA_QUALITY_BLOCK" in denied["output"]["reasoning_summary"]
    assert denied["output"]["requires_human_review"]  # data-quality denial requests human review
    allowed = orchestrator.handle(AgentQuery("EXPLAIN_RETRAINING", {"retraining_decision": RETRAIN_ALLOW}))
    assert "allowed" in allowed["output"]["reasoning_summary"]
    assert "RETRAINING_ALLOWED" in allowed["output"]["reasoning_summary"]


def test_agent_can_explain_promotion_and_rollback(orchestrator):
    promotion = orchestrator.handle(AgentQuery("EXPLAIN_PROMOTION", {"promotion_decision": PROMOTION_REJECT}))
    summary = promotion["output"]["reasoning_summary"]
    assert "REJECT" in summary and "BENCHMARK_GATE" in summary
    assert "Improved MAE alone" in summary and "not have been sufficient" in summary
    rollback = orchestrator.handle(AgentQuery("EXPLAIN_ROLLBACK", {"rollback_record": ROLLBACK}))
    summary = rollback["output"]["reasoning_summary"]
    assert "ROLLBACK_COMPLETED" in summary and "verification" in summary.lower()
    assert rollback["output"]["agent_id"] == "GOVERNANCE_EXPLANATION_AGENT"


def test_agent_can_generate_report(orchestrator):
    result = orchestrator.handle(AgentQuery("GENERATE_REPORT", {
        "report_kind": "INCIDENT_REPORT", "drift_event": DRIFT_EVENT, "retraining_decision": RETRAIN_DENY,
        "evidence_refs": ["e.jsonl"]}))
    output = result["output"]
    assert output["recommendation"] == "CREATE_REPORT" and not output["blocked"]
    assert "Drift incident" in output["recommendation_text"] and "Governance response" in output["recommendation_text"]
    kinds = orchestrator.handle(AgentQuery("GENERATE_REPORT", {"report_kind": "EXPERIMENT_SUMMARY",
                                                              "adaptation_rows": [{"target": "load", "scenario": "s", "reference_mae": 1, "challenger_mae": 0.5, "adaptation_gain_percent": 50.0}]}))
    assert "Adaptation experiment results" in kinds["output"]["recommendation_text"]
    unknown = orchestrator.handle(AgentQuery("GENERATE_REPORT", {"report_kind": "NOT_A_KIND"}))
    assert "Unknown report kind" in unknown["output"]["reasoning_summary"]


def test_output_contract_enforced_on_every_result(orchestrator):
    result = orchestrator.handle(AgentQuery("EXPLAIN_DRIFT", {"drift_event": DRIFT_EVENT}))
    assert_valid_output(result["output"])
    with pytest.raises(ValueError):
        assert_valid_output({f: result["output"].get(f) for f in OUTPUT_CONTRACT_FIELDS[:-1]})
    with pytest.raises(ValueError):
        assert_structured_evidence("not-a-dict")


@pytest.mark.parametrize("unsafe", sorted(BLOCKED_RECOMMENDATIONS))
def test_agent_cannot_promote_rollback_retrain_or_change_policy_or_features(orchestrator, unsafe):
    result = orchestrator.handle(AgentQuery("EXPLAIN_PROMOTION", {
        "promotion_decision": PROMOTION_REJECT, "advisory_recommendation_type": unsafe,
        "advisory_text": "untrusted suggestion"}))
    assert result["output"]["blocked"] and not result["firewall"]["allowed"]
    assert result["output"]["block_reason"] in ("UNSAFE_RECOMMENDATION_BLOCKED",)
    assert result["output"]["recommendation"] == unsafe  # recorded, but neutralized


def test_agent_cannot_access_final_test(orchestrator):
    result = orchestrator.handle(AgentQuery("RETRIEVE_EVIDENCE", {"source": "final_test_labels"}))
    assert result["output"]["blocked"] and result["output"]["block_reason"] == "AGENT_FINAL_TEST_ACCESS_BLOCKED"
    with pytest.raises(ValueError):
        assert_no_final_test_access("data/final_test/november.parquet")
    retriever = EvidenceRetrievalAgent(ROOT)
    blocked = retriever.analyze(AgentQuery("RETRIEVE_EVIDENCE", {"source": "december_targets"}))
    assert blocked.blocked


def test_firewall_allows_advisory_types_only():
    for allowed in sorted(ALLOWED_RECOMMENDATIONS):
        assert firewall_validate(allowed).allowed
    for blocked in sorted(BLOCKED_RECOMMENDATIONS):
        result = firewall_validate(blocked)
        assert not result.allowed and result.reason_code == "UNSAFE_RECOMMENDATION_BLOCKED"
    unknown = firewall_validate("DEPLOY_EVERYTHING")
    assert not unknown.allowed and unknown.reason_code == "UNKNOWN_RECOMMENDATION_BLOCKED"


def test_audit_logs_agent_actions_and_rejects_forbidden_events(tmp_path):
    audit_path = tmp_path / "audit.jsonl"
    orch = Orchestrator(ROOT, audit_path=audit_path, memory_dir=tmp_path / "memory")
    orch.handle(AgentQuery("EXPLAIN_DRIFT", {"drift_event": DRIFT_EVENT}))
    orch.handle(AgentQuery("EXPLAIN_PROMOTION", {"promotion_decision": PROMOTION_REJECT,
                                                 "advisory_recommendation_type": "PROMOTE_MODEL"}))
    events = read_agent_events(audit_path)
    types = [e["event_type"] for e in events]
    assert "AGENT_QUERY_RECEIVED" in types and "AGENT_ANALYSIS_COMPLETED" in types
    assert "AGENT_RECOMMENDATION_CREATED" in types and "AGENT_RECOMMENDATION_BLOCKED" in types
    assert all(e["actor_type"] == "AGENT" and e["phase"] == "17" for e in events)
    with pytest.raises(ValueError):
        agent_emit(audit_path, "AGENT_MODEL_PROMOTED", "x", {})
    with pytest.raises(ValueError):
        agent_emit(audit_path, "AGENT_RETRAINING_STARTED", "x", {})
    assert_no_forbidden_agent_events(["AGENT_RECOMMENDATION_CREATED"])


def test_human_review_requested_event_emitted(tmp_path):
    audit_path = tmp_path / "audit.jsonl"
    orch = Orchestrator(ROOT, audit_path=audit_path, memory_dir=tmp_path / "memory")
    orch.handle(AgentQuery("EXPLAIN_RETRAINING", {"retraining_decision": RETRAIN_DENY}))
    types = [e["event_type"] for e in read_agent_events(audit_path)]
    assert "HUMAN_REVIEW_REQUESTED" in types


def test_memory_stores_only_structured_fields_no_chain_of_thought(orchestrator, tmp_path):
    payload = {"drift_event": DRIFT_EVENT, "secret_prompt": "SYSTEM PROMPT", "chain_of_thought": "private reasoning"}
    result = orchestrator.handle(AgentQuery("EXPLAIN_DRIFT", payload))
    memory = MemoryStore(tmp_path / "memory")
    record = result["memory_record"]
    assert set(record) <= set(MEMORY_FIELDS)
    assert "chain_of_thought" not in record and "secret_prompt" not in record
    assert "prompt" not in json.dumps(memory.read()).lower()
    assert "chain" not in json.dumps(memory.read()).lower()


def test_backend_abstraction_deterministic_and_llm_unimplemented():
    backend = LocalRuleBackend()
    assert backend.backend_type == "LOCAL_RULE_BASED"
    assert backend.analyze("DRIFT_ANALYSIS_AGENT", "EXPLAIN_DRIFT", {}) == ""
    with pytest.raises(NotImplementedError):
        LLMBackendInterface()


def test_deterministic_output_and_missing_evidence_handling(orchestrator):
    first = orchestrator.handle(AgentQuery("EXPLAIN_DRIFT", {"drift_event": DRIFT_EVENT}))
    second = orchestrator.handle(AgentQuery("EXPLAIN_DRIFT", {"drift_event": DRIFT_EVENT}))
    assert first["output"]["reasoning_summary"] == second["output"]["reasoning_summary"]
    missing = orchestrator.handle(AgentQuery("EXPLAIN_DRIFT", {"drift_event": None}))
    assert "No drift event" in missing["output"]["reasoning_summary"] and not missing["output"]["blocked"]
    unknown_source = EvidenceRetrievalAgent(ROOT).retrieve("nonexistent_source")
    assert unknown_source["status"] == "NO_EVIDENCE" and unknown_source["records"] == []


def test_planner_routes_and_rejects_unknown_queries():
    planner = Planner(ROOT)
    assert planner.route("EXPLAIN_DRIFT").agent_id == "DRIFT_ANALYSIS_AGENT"
    assert planner.route("EXPLAIN_PROMOTION").agent_id == "GOVERNANCE_EXPLANATION_AGENT"
    with pytest.raises(ValueError):
        planner.route("PROMOTE_THE_MODEL")


def test_phase17_freeze_valid_and_runner_has_no_forbidden_flags():
    import hashlib
    freeze = json.loads((ROOT / "artifacts/experimental_design/phase_17_agent_protocol_freeze.yaml").read_text())
    assert freeze["allowed_actions"] == ["INVESTIGATE", "SUMMARIZE", "EXPLAIN", "REQUEST_HUMAN_REVIEW", "CREATE_REPORT"]
    assert set(freeze["blocked_actions"]) == BLOCKED_RECOMMENDATIONS
    assert freeze["final_test_isolation"]["phase_17_new_final_test_reads"] == 0
    recorded = (ROOT / "artifacts/experimental_design/phase_17_agent_protocol_freeze.sha256").read_text().split()[0]
    assert hashlib.sha256((ROOT / "artifacts/experimental_design/phase_17_agent_protocol_freeze.yaml").read_bytes()).hexdigest() == recorded
    source = (ROOT / "scripts/run_agent_scenarios.py").read_text(encoding="utf-8")
    assert '"--final-test"' not in source and "'--final-test'" not in source
    assert "--hpo" not in source


def test_official_scenario_results_when_present():
    path = ROOT / "artifacts/agents/phase_17/scenario_results/agent_scenarios.json"
    if not path.exists():
        pytest.skip("official run not executed yet")
    data = json.loads(path.read_text())
    metrics = data["metrics"]
    assert all(c["correct"] for c in metrics["cases"])
    assert metrics["safety"]["blocked_unsafe_recommendations"] == 3
    assert metrics["safety"]["governance_bypasses"] == 0
    assert metrics["reliability"]["deterministic_output_structure"] is True
    assert metrics["report_created"] is True
