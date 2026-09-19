"""Evidence retrieval agent: bounded, registered sources only.

Can retrieve drift evidence, governance/retraining decisions, registries,
lineage, and audits. Cannot retrieve future or final-test data; unknown or
final-test-marked sources are blocked or gracefully reported as missing."""
from __future__ import annotations
import json
import time
from pathlib import Path
from .base import Agent, LocalRuleBackend
from .schemas import AgentOutput, AgentQuery
from .validation import assert_no_final_test_access

SOURCES = {
    "drift_events_phase15": "artifacts/retraining/phase_15/evidence/drift_events.jsonl",
    "drift_events_phase14": "artifacts/monitoring/phase_14/events/drift_events.jsonl",
    "retraining_decisions": "artifacts/retraining/phase_15/decisions/retraining_decisions.jsonl",
    "challenger_registry": "artifacts/model_registry/phase_15_challengers.yaml",
    "champion_registry": "artifacts/model_registry/phase_16_champion_registry.yaml",
    "lifecycle_registry": "artifacts/model_registry/lifecycle_registry.yaml",
    "lineage_index": "artifacts/mlops/lineage/lineage_index.yaml",
    "promotion_evaluations": "artifacts/champion_challenger/phase_16/evaluations/real_phase15_challengers.json",
    "retraining_evaluations": "artifacts/retraining/phase_15/evaluations",
}


class EvidenceRetrievalAgent(Agent):
    agent_id = "EVIDENCE_RETRIEVAL_AGENT"
    agent_version = "1.0.0"

    def __init__(self, project_root: Path, backend: LocalRuleBackend | None = None):
        super().__init__(backend or LocalRuleBackend())
        self.project_root = Path(project_root)

    def retrieve(self, source: str, limit: int = 5, subject_id: str | None = None) -> dict:
        assert_no_final_test_access(source)
        if source not in SOURCES:
            return {"status": "NO_EVIDENCE", "reason": f"Unknown source '{source}'",
                    "records": [], "evidence_refs": []}
        path = self.project_root / SOURCES[source]
        if not path.exists():
            return {"status": "NO_EVIDENCE", "reason": f"Source '{source}' has no data yet",
                    "records": [], "evidence_refs": []}
        started = time.perf_counter()
        records: list
        if subject_id and source == "lineage_index":
            from smartgrid_mlops.mlops.lineage import LineageGraph
            graph = LineageGraph.load(path)
            if subject_id not in graph.nodes:
                return {"status": "NO_EVIDENCE", "reason": f"Subject '{subject_id}' not in lineage index",
                        "records": [], "evidence_refs": []}
            records = graph.trace(subject_id)
        elif path.suffix == ".jsonl":
            records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        else:
            records = [json.loads(path.read_text(encoding="utf-8"))]
        records = records[-limit:] if not subject_id else records
        return {"status": "OK", "records": records, "evidence_refs": [SOURCES[source]],
                "retrieval_seconds": time.perf_counter() - started}

    def analyze(self, query: AgentQuery) -> AgentOutput:
        source = query.payload.get("source", "")
        subject = query.payload.get("subject_id")
        try:
            result = self.retrieve(source, subject_id=subject)
            blocked = False
        except ValueError as error:
            result = {"status": "BLOCKED", "reason": str(error), "records": [], "evidence_refs": []}
            blocked = True
        if blocked:
            summary = f"Evidence retrieval blocked: {result['reason']}"
            recommendation, confidence, review = "REQUEST_HUMAN_REVIEW", 0.3, True
        elif result["status"] == "OK":
            summary = f"Retrieved {len(result['records'])} structured records from registered source '{source}'."
            recommendation, confidence, review = "SUMMARIZE", 0.9, False
        else:
            summary = f"No evidence available: {result['reason']}"
            recommendation, confidence, review = "EXPLAIN", 0.5, False
        output = AgentOutput(
            agent_id=self.agent_id, agent_version=self.agent_version, query_id=query.query_id,
            input_evidence_refs=result["evidence_refs"], reasoning_summary=summary,
            recommendation=recommendation,
            recommendation_text="Registered-source retrieval only; final-test and future data are unreachable.",
            confidence=confidence,
            limitations="Retrieval is limited to registered development-phase sources; no raw filesystem access.",
            requires_human_review=review, query_type=query.query_type)
        if blocked:
            output.blocked = True
            output.block_reason = "AGENT_FINAL_TEST_ACCESS_BLOCKED"
        return output
