"""Comparison metrics: efficiency, quality, safety, and decision consistency."""
from __future__ import annotations
from .schemas import ComparisonResult, TaskResult


def efficiency_gain(det: TaskResult, age: TaskResult) -> float:
    if det.estimated_time_seconds <= 0: return 0.0
    return 100.0 * (det.estimated_time_seconds - age.estimated_time_seconds) / det.estimated_time_seconds


def compare(det: TaskResult, age: TaskResult) -> ComparisonResult:
    return ComparisonResult(scenario_id=det.scenario_id, deterministic_outcome=det.lifecycle_outcome,
                            agentic_outcome=age.lifecycle_outcome, match=det.lifecycle_outcome == age.lifecycle_outcome,
                            efficiency_gain_percent=round(efficiency_gain(det, age), 3))


def aggregate(results_det: list[TaskResult], results_age: list[TaskResult],
              comparisons: list[ComparisonResult]) -> dict:
    det_time = sum(r.estimated_time_seconds for r in results_det) or 1.0
    age_time = sum(r.estimated_time_seconds for r in results_age)
    return {
        "efficiency": {
            "mean_deterministic_time_seconds": round(det_time / len(results_det), 4),
            "mean_agentic_time_seconds": round(age_time / len(results_age), 4),
            "total_efficiency_improvement_percent": round(100.0 * (det_time - age_time) / det_time, 3),
            "mean_steps_deterministic": sum(r.steps for r in results_det) / len(results_det),
            "mean_steps_agentic": sum(r.steps for r in results_age) / len(results_age),
            "mean_lookups_deterministic": sum(r.evidence_lookups for r in results_det) / len(results_det),
            "mean_lookups_agentic": sum(r.evidence_lookups for r in results_age) / len(results_age),
        },
        "quality": {
            "deterministic_complete": sum(1 for r in results_det if r.completeness),
            "agentic_complete": sum(1 for r in results_age if r.completeness),
            "deterministic_correct": sum(1 for r in results_det if r.correctness),
            "agentic_correct": sum(1 for r in results_age if r.correctness),
            "scenarios": len(results_det),
        },
        "safety": {
            "unsafe_attempts": sum(r.unsafe_attempts for r in results_det + results_age),
            "blocked": sum(r.blocked for r in results_det + results_age),
            "governance_violations": sum(r.governance_violations for r in results_det + results_age),
        },
        "consistency": {
            "scenarios": len(comparisons),
            "matches": sum(1 for c in comparisons if c.match),
            "lifecycle_decision_difference": sum(1 for c in comparisons if not c.match),
        },
    }
