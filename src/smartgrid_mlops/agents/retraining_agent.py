"""Retraining explanation agent: explains Phase 15 retraining decisions.

Cannot rerun retraining; output is advisory only."""
from __future__ import annotations
from .base import Agent
from .schemas import AgentOutput, AgentQuery


class RetrainingExplanationAgent(Agent):
    agent_id = "RETRAINING_EXPLANATION_AGENT"
    agent_version = "1.0.0"

    def analyze(self, query: AgentQuery) -> AgentOutput:
        decision = query.payload.get("retraining_decision")
        refs = [str(x) for x in query.payload.get("evidence_refs", [])]
        if not decision:
            return AgentOutput(
                agent_id=self.agent_id, agent_version=self.agent_version, query_id=query.query_id,
                input_evidence_refs=[], reasoning_summary="No retraining decision was supplied.",
                recommendation="EXPLAIN", recommendation_text="Provide a structured RetrainingDecision.",
                confidence=0.2, limitations="Missing evidence handled gracefully.",
                requires_human_review=False, query_type=query.query_type)
        verdict = decision.get("decision", "UNKNOWN")
        reasons = decision.get("reason_codes", [])
        failed_gates = [g["gate"] for g in decision.get("gate_results", []) if not g.get("passed")]
        if verdict == "ALLOW":
            summary = (f"Retraining was allowed for target '{decision.get('target', 'unknown')}' "
                       f"(scenario {decision.get('simulation_scenario_id') or 'n/a'}): all {len(decision.get('gate_results', []))} "
                       f"eligibility gates passed under policy version {decision.get('policy_version', 'unknown')}. "
                       f"Reason codes: {', '.join(reasons)}.")
            recommendation, review = "SUMMARIZE", False
        elif verdict == "DEFER":
            summary = (f"Retraining was deferred for target '{decision.get('target', 'unknown')}': "
                       f"{', '.join(reasons)}. The request is premature but potentially valid; "
                       f"it may be re-evaluated once the blocking conditions change.")
            recommendation, review = "EXPLAIN", True
        else:
            summary = (f"Retraining was denied for target '{decision.get('target', 'unknown')}' because: "
                       f"{'; '.join(reasons)}. Failed gates: {', '.join(failed_gates) or 'recorded in reason codes'}.")
            recommendation, review = "EXPLAIN", "DATA_QUALITY_BLOCK" in reasons
        return AgentOutput(
            agent_id=self.agent_id, agent_version=self.agent_version, query_id=query.query_id,
            input_evidence_refs=refs or ["artifacts/retraining/phase_15/decisions/retraining_decisions.jsonl"],
            reasoning_summary=summary, recommendation=recommendation,
            recommendation_text=("Advisory only: this explanation cannot rerun, approve, or start retraining. "
                                 "Any new attempt must pass the deterministic Phase 15 retraining policy."),
            confidence=0.9,
            limitations="Explanation derives from the recorded gate results; it does not re-evaluate evidence.",
            requires_human_review=review, query_type=query.query_type)
