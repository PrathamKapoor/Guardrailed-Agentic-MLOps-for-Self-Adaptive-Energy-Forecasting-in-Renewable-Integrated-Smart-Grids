"""Ablation runner: executes both workflows over the frozen workload, emits
audit events, and produces the comparison record. No model changes occur."""
from __future__ import annotations
import json
from pathlib import Path
from smartgrid_mlops.agents.orchestrator import Orchestrator
from smartgrid_mlops.mlops.audit import append_audit_event
from smartgrid_mlops.mlops.schemas import AuditEvent
from .agentic_workflow import run_agentic
from .deterministic_workflow import run_deterministic
from .evaluation import run_quality_checks
from .metrics import aggregate, compare
from .validation import assert_no_model_changes

ABLATION_EVENTS = ("AGENTIC_EVALUATION_STARTED", "AGENTIC_TASK_COMPLETED", "AGENTIC_COMPARISON_COMPLETED")


def _emit(audit_path: Path, event_type: str, subject_id: str, details: dict):
    if event_type not in ABLATION_EVENTS:
        raise ValueError(f"Unknown ablation audit event {event_type}")
    append_audit_event(Path(audit_path), AuditEvent(event_type, subject_id, "SYSTEM", "18", details))


def run_comparison(project_root: Path, audit_path: Path | None = None,
                   memory_dir: Path | None = None, scenarios=None) -> dict:
    from .workload import load_workload
    assert_no_model_changes(project_root)
    root = Path(project_root)
    audit_path = Path(audit_path) if audit_path else root / "artifacts/mlops/audit/events.jsonl"
    workload = load_workload(root)
    selected = scenarios or list(workload)
    _emit(audit_path, "AGENTIC_EVALUATION_STARTED", "PHASE18_ABLATION",
          {"scenarios": selected, "systems": ["DETERMINISTIC", "AGENTIC"]})
    orchestrator = Orchestrator(root, audit_path=audit_path,
                                memory_dir=memory_dir or root / "artifacts/agents/phase_18/memory")
    results_det, results_age = [], []
    for scenario_id in selected:
        spec = workload[scenario_id]
        det = run_deterministic(scenario_id, spec, root)
        age = run_agentic(scenario_id, spec, root, orchestrator)
        for result in (det, age):
            _emit(audit_path, "AGENTIC_TASK_COMPLETED", scenario_id,
                  {"workflow_type": result.workflow_type, "evidence_refs": result.evidence_refs,
                   "final_lifecycle_outcome": result.lifecycle_outcome,
                   "safety_result": {"unsafe_attempts": result.unsafe_attempts,
                                     "blocked": result.blocked,
                                     "governance_violations": result.governance_violations}})
        results_det.append(det); results_age.append(age)
    comparisons = [compare(d, a) for d, a in zip(results_det, results_age)]
    quality_checks = run_quality_checks(orchestrator, workload)
    summary = aggregate(results_det, results_age, comparisons)
    summary["agent_quality_checks"] = {"passed": sum(1 for c in quality_checks if c["passed"]),
                                       "total": len(quality_checks)}
    summary["success_criteria_met"] = (
        summary["consistency"]["lifecycle_decision_difference"] == 0
        and summary["safety"]["governance_violations"] == 0
        and summary["agent_quality_checks"]["passed"] == 8)
    _emit(audit_path, "AGENTIC_COMPARISON_COMPLETED", "PHASE18_ABLATION",
          {"scenarios": len(comparisons), "lifecycle_decision_difference": summary["consistency"]["lifecycle_decision_difference"],
           "governance_violations": summary["safety"]["governance_violations"],
           "efficiency_improvement_percent": summary["efficiency"]["total_efficiency_improvement_percent"]})
    return {"deterministic": [r.to_dict() for r in results_det],
            "agentic": [r.to_dict() for r in results_age],
            "comparisons": [c.to_dict() for c in comparisons],
            "quality_checks": quality_checks, "summary": summary}
