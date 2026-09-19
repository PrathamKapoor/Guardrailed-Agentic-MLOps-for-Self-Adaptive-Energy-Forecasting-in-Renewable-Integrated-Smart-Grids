from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

FINAL_TEST_TAGS = {
    "final_test_training_access": "NO", "final_test_hpo_access": "NO",
    "final_test_selection_access": "NO", "final_test_performance_access": "NO",
}

REGISTRY_STATES = {"SPEC_FROZEN", "REGISTERED_REFERENCE", "REGISTERED_CHALLENGER", "INELIGIBLE", "ARCHIVED", "INVALIDATED"}
RESEARCH_ROLES = {"REFERENCE", "CHALLENGER", "BASELINE_COMPARATOR", "AUDIT_ONLY"}
BENCHMARK_GATES = {"BENCHMARK_GATE_PASS", "BENCHMARK_GATE_FAIL", "NOT_APPLICABLE"}


@dataclass(frozen=True)
class AuditEvent:
    event_type: str
    subject_id: str
    actor_type: str
    phase: str
    details: dict[str, Any] = field(default_factory=dict)
    evidence_refs: list[str] = field(default_factory=list)
    event_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
