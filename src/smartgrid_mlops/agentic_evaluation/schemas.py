from __future__ import annotations
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

WORKFLOW_TYPES = ("DETERMINISTIC", "AGENTIC")

# Frozen operational cost model (human-inspection approximation; no real operators):
COST_MODEL = {
    "per_artifact_inspection_seconds": 3.0,
    "per_record_scan_seconds": 0.05,
    "agent_summary_reading_seconds": 2.0,
    "agent_verification_inspection_seconds": 3.0,
}

AGENT_QUALITY_CHECKS = {
    "A01": "correct drift explanation",
    "A02": "correct retraining explanation",
    "A03": "correct promotion explanation",
    "A04": "correct rollback explanation",
    "A05": "missing evidence handling",
    "A06": "conflicting evidence handling",
    "A07": "unsafe request refusal",
    "A08": "final-test request refusal",
}

ABLATION_AUDIT_EVENTS = ("AGENTIC_EVALUATION_STARTED", "AGENTIC_TASK_COMPLETED", "AGENTIC_COMPARISON_COMPLETED")


@dataclass
class TaskResult:
    scenario_id: str
    workflow_type: str
    steps: int
    evidence_lookups: int
    estimated_time_seconds: float
    completeness: bool
    correctness: bool
    evidence_refs: list[str]
    derived_facts: dict
    lifecycle_outcome: str
    unsafe_attempts: int = 0
    blocked: int = 0
    governance_violations: int = 0
    measured_agent_seconds: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]: return asdict(self)


@dataclass
class ComparisonResult:
    scenario_id: str
    deterministic_outcome: str
    agentic_outcome: str
    match: bool
    efficiency_gain_percent: float
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]: return asdict(self)
