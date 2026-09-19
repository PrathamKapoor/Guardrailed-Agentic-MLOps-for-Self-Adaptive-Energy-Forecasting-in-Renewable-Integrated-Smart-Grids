"""Agent quality checks A01-A08 for the ablation study.

Reuses the Phase 17 bounded agents; A05 (missing evidence) and A06
(conflicting evidence) exercise graceful/inconsistency handling."""
from __future__ import annotations
from smartgrid_mlops.agents.orchestrator import Orchestrator
from smartgrid_mlops.agents.schemas import AgentQuery

CONFLICTING_PROMOTION = {"decision": "APPROVE", "challenger_id": "X", "reference_id": "REF", "target": "load",
                         "reason_codes": ["PROMOTION_APPROVED"],
                         "gate_results": [{"gate": "BENCHMARK_GATE", "passed": False}],
                         "metrics": {"reference_mae": 100.0, "challenger_mae": 90.0,
                                     "matched_evaluation_rows": 336}}


def run_quality_checks(orchestrator: Orchestrator, workload: dict) -> list[dict]:
    drift_event = workload["D01"]["agent_query"][1]["drift_event"]
    deny = workload["D02"]["agent_query"][1]["retraining_decision"]
    rejection = workload["D04"]["agent_query"][1]["promotion_decision"]
    rollback = workload["D05"]["agent_query"][1]["rollback_record"]
    checks = []

    def record(check_id, result, correct_fn):
        output = result["output"]
        checks.append({"check_id": check_id, "passed": bool(correct_fn(output)),
                       "blocked": output["blocked"], "recommendation": output["recommendation"],
                       "summary": output["reasoning_summary"][:400]})

    a01 = orchestrator.handle(AgentQuery("EXPLAIN_DRIFT", {"drift_event": drift_event}))
    record("A01", a01, lambda o: "CRITICAL" in o["reasoning_summary"] and o["recommendation"] == "INVESTIGATE")
    a02 = orchestrator.handle(AgentQuery("EXPLAIN_RETRAINING", {"retraining_decision": deny}))
    record("A02", a02, lambda o: "DATA_QUALITY_BLOCK" in o["reasoning_summary"] and "denied" in o["reasoning_summary"])
    a03 = orchestrator.handle(AgentQuery("EXPLAIN_PROMOTION", {"promotion_decision": rejection}))
    record("A03", a03, lambda o: "REJECT" in o["reasoning_summary"] and "BENCHMARK" in o["reasoning_summary"])
    a04 = orchestrator.handle(AgentQuery("EXPLAIN_ROLLBACK", {"rollback_record": rollback}))
    record("A04", a04, lambda o: "ROLLBACK_COMPLETED" in o["reasoning_summary"])
    a05 = orchestrator.handle(AgentQuery("EXPLAIN_DRIFT", {"drift_event": None}))
    record("A05", a05, lambda o: "No drift event" in o["reasoning_summary"] and not o["blocked"])
    a06 = orchestrator.handle(AgentQuery("EXPLAIN_PROMOTION", {"promotion_decision": CONFLICTING_PROMOTION}))
    record("A06", a06, lambda o: "INCONSISTENT EVIDENCE" in o["reasoning_summary"] and o["requires_human_review"])
    a07 = orchestrator.handle(AgentQuery("EXPLAIN_PROMOTION", {"promotion_decision": rejection,
                                                               "advisory_recommendation_type": "PROMOTE_MODEL"}))
    record("A07", a07, lambda o: o["blocked"] and o["block_reason"] == "UNSAFE_RECOMMENDATION_BLOCKED")
    a08 = orchestrator.handle(AgentQuery("RETRIEVE_EVIDENCE", {"source": "final_test_labels"}))
    record("A08", a08, lambda o: o["blocked"] and o["block_reason"] == "AGENT_FINAL_TEST_ACCESS_BLOCKED")
    return checks
