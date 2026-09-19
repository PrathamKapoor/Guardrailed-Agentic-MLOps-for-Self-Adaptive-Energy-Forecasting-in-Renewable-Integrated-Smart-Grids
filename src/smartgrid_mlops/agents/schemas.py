from __future__ import annotations
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

ALLOWED_RECOMMENDATIONS = {"INVESTIGATE", "SUMMARIZE", "EXPLAIN", "REQUEST_HUMAN_REVIEW", "CREATE_REPORT"}
BLOCKED_RECOMMENDATIONS = {"PROMOTE_MODEL", "ROLLBACK_MODEL", "CHANGE_POLICY", "START_RETRAINING", "CHANGE_FEATURES"}


QUERY_TYPES = {
    "EXPLAIN_DRIFT": "DRIFT_ANALYSIS_AGENT",
    "EXPLAIN_RETRAINING": "RETRAINING_EXPLANATION_AGENT",
    "EXPLAIN_PROMOTION": "GOVERNANCE_EXPLANATION_AGENT",
    "EXPLAIN_ROLLBACK": "GOVERNANCE_EXPLANATION_AGENT",
    "GENERATE_REPORT": "REPORT_GENERATION_AGENT",
    "RETRIEVE_EVIDENCE": "EVIDENCE_RETRIEVAL_AGENT",
}

AGENT_IDS = {
    "DRIFT_ANALYSIS_AGENT": "1.0.0",
    "RETRAINING_EXPLANATION_AGENT": "1.0.0",
    "GOVERNANCE_EXPLANATION_AGENT": "1.0.0",
    "REPORT_GENERATION_AGENT": "1.0.0",
    "EVIDENCE_RETRIEVAL_AGENT": "1.0.0",
}

OUTPUT_CONTRACT_FIELDS = ("agent_id", "agent_version", "timestamp", "input_evidence_refs",
                          "reasoning_summary", "recommendation", "confidence", "limitations",
                          "requires_human_review")

# Memory may store ONLY these fields: no chain-of-thought, prompts, or private traces.
MEMORY_FIELDS = OUTPUT_CONTRACT_FIELDS + ("query_id", "query_type", "firewall", "advisory_text_untrusted")

AGENT_AUDIT_EVENT_TYPES = (
    "AGENT_QUERY_RECEIVED", "AGENT_ANALYSIS_COMPLETED", "AGENT_RECOMMENDATION_CREATED",
    "AGENT_RECOMMENDATION_BLOCKED", "HUMAN_REVIEW_REQUESTED",
)

FORBIDDEN_AUDIT_EVENT_TYPES = ("AGENT_MODEL_PROMOTED", "AGENT_RETRAINING_STARTED")

FINAL_TEST_MARKERS = ("final_test", "final-test", "november", "december")


@dataclass(frozen=True)
class AgentQuery:
    query_type: str
    payload: dict
    query_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]: return asdict(self)


@dataclass
class AgentOutput:
    agent_id: str
    agent_version: str
    query_id: str
    input_evidence_refs: list[str]
    reasoning_summary: str
    recommendation: str
    recommendation_text: str
    confidence: float
    limitations: str
    requires_human_review: bool
    query_type: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    advisory_text_untrusted: str = ""
    blocked: bool = False
    block_reason: str = ""

    def to_dict(self) -> dict[str, Any]: return asdict(self)

    def scientific_content(self) -> dict[str, Any]:
        value = self.to_dict()
        value.pop("timestamp", None)
        value.pop("query_id", None)
        return value

    def memory_record(self, firewall_result: dict | None = None) -> dict[str, Any]:
        record = {key: self.to_dict()[key] for key in MEMORY_FIELDS if key in self.to_dict()}
        record["firewall"] = firewall_result or {}
        return record
