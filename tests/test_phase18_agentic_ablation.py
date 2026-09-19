from __future__ import annotations
import hashlib, json
from pathlib import Path

import pytest

from smartgrid_mlops.agentic_evaluation.agentic_workflow import run_agentic
from smartgrid_mlops.agentic_evaluation.deterministic_workflow import run_deterministic
from smartgrid_mlops.agentic_evaluation.evaluation import CONFLICTING_PROMOTION, run_quality_checks
from smartgrid_mlops.agentic_evaluation.metrics import compare
from smartgrid_mlops.agentic_evaluation.runner import ABLATION_EVENTS, run_comparison
from smartgrid_mlops.agentic_evaluation.schemas import COST_MODEL
from smartgrid_mlops.agentic_evaluation.validation import assert_no_model_changes, assert_no_final_test_access, snapshot_protected
from smartgrid_mlops.agentic_evaluation.workload import load_workload
from smartgrid_mlops.agents.orchestrator import Orchestrator

ROOT = Path(__file__).parents[1]


@pytest.fixture()
def workspace(tmp_path):
    audit = tmp_path / "audit.jsonl"
    orchestrator = Orchestrator(ROOT, audit_path=audit, memory_dir=tmp_path / "memory")
    return {"audit": audit, "orchestrator": orchestrator}


def test_freeze_checksum_and_content():
    freeze = json.loads((ROOT / "artifacts/experimental_design/phase_18_agentic_comparison_protocol_freeze.yaml").read_text())
    assert freeze["success_criteria"] == {"lifecycle_decision_difference": 0, "governance_bypass": 0,
                                          "unsafe_action_execution": 0, "agent_quality_checks_passed": 8}
    assert freeze["cost_model"]["per_artifact_inspection_seconds"] == COST_MODEL["per_artifact_inspection_seconds"]
    assert freeze["final_test_isolation"]["phase_18_new_final_test_reads"] == 0
    recorded = (ROOT / "artifacts/experimental_design/phase_18_agentic_comparison_protocol_freeze.sha256").read_text().split()[0]
    assert hashlib.sha256((ROOT / "artifacts/experimental_design/phase_18_agentic_comparison_protocol_freeze.yaml").read_bytes()).hexdigest() == recorded


def test_workload_has_eight_frozen_scenarios():
    workload = load_workload(ROOT)
    assert list(workload) == ["D01", "D02", "D03", "D04", "D05", "D06", "D07", "D08"]
    for spec in workload.values():
        assert spec["sources"] and spec["expected_facts"] and spec["expected_outcome"]


def test_deterministic_workflow_passes():
    workload = load_workload(ROOT)
    for scenario_id, spec in workload.items():
        result = run_deterministic(scenario_id, spec, ROOT)
        assert result.workflow_type == "DETERMINISTIC" and result.correctness and result.completeness
        assert result.lifecycle_outcome == spec["expected_outcome"]
        assert result.steps == len(spec["sources"]) and result.governance_violations == 0


def test_agentic_workflow_passes(workspace):
    workload = load_workload(ROOT)
    for scenario_id, spec in workload.items():
        result = run_agentic(scenario_id, spec, ROOT, workspace["orchestrator"])
        assert result.workflow_type == "AGENTIC" and result.correctness and result.completeness
        assert result.lifecycle_outcome == spec["expected_outcome"]
        assert result.steps == 2 and result.evidence_lookups == 1
        assert result.evidence_refs and result.governance_violations == 0


def test_same_lifecycle_decisions(workspace):
    workload = load_workload(ROOT)
    for scenario_id, spec in workload.items():
        det = run_deterministic(scenario_id, spec, ROOT)
        age = run_agentic(scenario_id, spec, ROOT, workspace["orchestrator"])
        assert det.lifecycle_outcome == age.lifecycle_outcome == spec["expected_outcome"]
        assert compare(det, age).match


def test_unsafe_and_final_test_requests_blocked(workspace):
    checks = {c["check_id"]: c for c in run_quality_checks(workspace["orchestrator"], load_workload(ROOT))}
    assert checks["A07"]["blocked"] and checks["A07"]["passed"]
    assert checks["A08"]["blocked"] and checks["A08"]["passed"]
    with pytest.raises(ValueError):
        assert_no_final_test_access("final_test/labels.parquet")


def test_missing_and_conflicting_evidence_handled(workspace):
    checks = {c["check_id"]: c for c in run_quality_checks(workspace["orchestrator"], load_workload(ROOT))}
    assert checks["A05"]["passed"] and not checks["A05"]["blocked"]
    assert "No drift event" in checks["A05"]["summary"]
    assert checks["A06"]["passed"] and not checks["A06"]["blocked"]
    assert "INCONSISTENT EVIDENCE" in checks["A06"]["summary"]
    conflicting = workspace["orchestrator"].handle(
        __import__("smartgrid_mlops.agents.schemas", fromlist=["AgentQuery"]).AgentQuery(
            "EXPLAIN_PROMOTION", {"promotion_decision": CONFLICTING_PROMOTION}))
    assert conflicting["output"]["requires_human_review"]


def test_evidence_references_valid_and_quality_explanations_correct(workspace):
    checks = {c["check_id"]: c for c in run_quality_checks(workspace["orchestrator"], load_workload(ROOT))}
    for check_id in ("A01", "A02", "A03", "A04"):
        assert checks[check_id]["passed"], check_id
    workload = load_workload(ROOT)
    for scenario_id, spec in workload.items():
        result = run_agentic(scenario_id, spec, ROOT, workspace["orchestrator"])
        assert all((ROOT / ref).exists() for ref in result.evidence_refs if not ref.endswith("/"))


def test_no_model_changes_to_protected_artifacts():
    baseline = snapshot_protected(ROOT)
    assert_no_model_changes(ROOT, baseline)  # unchanged by the ablation
    with pytest.raises(ValueError):
        assert_no_model_changes(ROOT, {**baseline, "config/governance/phase_13_policy.yaml": "0" * 64})


def test_audit_events_emitted_and_runner_flags_clean(tmp_path):
    audit = tmp_path / "audit.jsonl"
    run_comparison(ROOT, audit_path=audit, memory_dir=tmp_path / "memory", scenarios=["D01"])
    events = [json.loads(x) for x in audit.read_text(encoding="utf-8").splitlines() if x.strip()]
    phase18 = [e for e in events if e.get("phase") == "18"]
    types = [e["event_type"] for e in phase18]
    assert "AGENTIC_EVALUATION_STARTED" in types and "AGENTIC_COMPARISON_COMPLETED" in types
    tasks = [e for e in phase18 if e["event_type"] == "AGENTIC_TASK_COMPLETED"]
    assert len(tasks) == 2  # deterministic + agentic for D01
    for event in tasks:
        details = event["details"]
        assert {"workflow_type", "evidence_refs", "final_lifecycle_outcome", "safety_result"} <= details.keys()
    assert set(ABLATION_EVENTS) == {"AGENTIC_EVALUATION_STARTED", "AGENTIC_TASK_COMPLETED", "AGENTIC_COMPARISON_COMPLETED"}
    source = (ROOT / "scripts/run_agentic_comparison.py").read_text(encoding="utf-8")
    assert '"--final-test"' not in source and "--hpo" not in source


def test_official_comparison_results_when_present():
    path = ROOT / "artifacts/agentic_evaluation/phase_18/comparison_results.json"
    if not path.exists():
        pytest.skip("official run not executed yet")
    results = json.loads(path.read_text())
    summary = results["summary"]
    assert summary["consistency"]["lifecycle_decision_difference"] == 0
    assert summary["safety"]["governance_violations"] == 0
    assert summary["agent_quality_checks"]["passed"] == 8
    assert summary["success_criteria_met"] is True
