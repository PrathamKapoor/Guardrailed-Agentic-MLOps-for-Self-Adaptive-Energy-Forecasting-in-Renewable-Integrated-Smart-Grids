"""Governance explanation agent: explains Phase 13/16 promotion and rollback decisions.

Cannot override governance; output is advisory only."""
from __future__ import annotations
from .base import Agent
from .schemas import AgentOutput, AgentQuery


class GovernanceExplanationAgent(Agent):
    agent_id = "GOVERNANCE_EXPLANATION_AGENT"
    agent_version = "1.0.0"

    def analyze(self, query: AgentQuery) -> AgentOutput:
        refs = [str(x) for x in query.payload.get("evidence_refs", [])]
        if query.query_type == "EXPLAIN_ROLLBACK":
            return self._rollback(query, query.payload.get("rollback_record"), refs)
        return self._promotion(query, query.payload.get("promotion_decision"), refs)

    def _promotion(self, query: AgentQuery, decision, refs: list[str]) -> AgentOutput:
        if not decision:
            return self._missing(query, "promotion decision")
        gates = decision.get("gate_results", [])
        passed = [g["gate"] for g in gates if g.get("passed")]
        failed = [g["gate"] for g in gates if not g.get("passed")]
        metrics = decision.get("metrics", {})
        verdict = decision.get("decision", "UNKNOWN")
        summary = (f"Promotion decision for challenger '{decision.get('challenger_id', 'unknown')}' versus reference "
                   f"'{decision.get('reference_id', 'unknown')}' was {verdict}. "
                   f"Passed gates ({len(passed)}): {', '.join(passed) or 'none'}. "
                   f"Failed gates ({len(failed)}): {', '.join(failed) or 'none'}. "
                   f"Reasons: {'; '.join(decision.get('reason_codes', []))}. "
                   f"Matched evaluation: reference MAE {metrics.get('reference_mae')}, challenger MAE "
                   f"{metrics.get('challenger_mae')} over {metrics.get('matched_evaluation_rows')} matched rows. "
                   f"Improved MAE alone would not have been sufficient: benchmark and approval evidence are required.")
        inconsistent = verdict == "APPROVE" and bool(failed)
        if inconsistent:
            summary += " INCONSISTENT EVIDENCE: decision APPROVE conflicts with recorded failed gates; flagged for review."
        return AgentOutput(
            agent_id=self.agent_id, agent_version=self.agent_version, query_id=query.query_id,
            input_evidence_refs=refs or ["artifacts/champion_challenger/phase_16/evaluations/real_phase15_challengers.json"],
            reasoning_summary=summary,
            recommendation="EXPLAIN",
            recommendation_text=("Advisory only: this explanation cannot approve, reject, or promote any model. "
                                 "Governance authority remains with the deterministic Phase 16 policy."),
            confidence=0.5 if inconsistent else 0.9,
            limitations="Explanation derives from recorded gate results; it does not re-evaluate evidence or metrics.",
            requires_human_review=inconsistent, query_type=query.query_type)

    def _rollback(self, query: AgentQuery, record, refs: list[str]) -> AgentOutput:
        if not record:
            return self._missing(query, "rollback record")
        verification = record.get("verification", {})
        checks = verification.get("checks", {})
        summary = (f"Rollback outcome for promoted model '{record.get('promoted_model_id', 'unknown')}' was "
                   f"{record.get('outcome', 'UNKNOWN')}. Trigger: post-promotion degradation "
                   f"{record.get('degradation_percent')}% versus threshold {record.get('threshold_percent')}%. "
                   f"Restoration verification: {', '.join(f'{k}={v}' for k, v in checks.items()) or 'not recorded'}. "
                   f"Previous model '{record.get('previous_model_id', 'unknown')}' "
                   f"{'was restored after all checks passed' if record.get('outcome') == 'ROLLBACK_COMPLETED' else 'was NOT restored because verification failed'}.")
        return AgentOutput(
            agent_id=self.agent_id, agent_version=self.agent_version, query_id=query.query_id,
            input_evidence_refs=refs or ["artifacts/model_registry/phase_16_champion_registry.yaml"],
            reasoning_summary=summary, recommendation="EXPLAIN",
            recommendation_text=("Advisory only: this explanation cannot execute or block rollbacks. "
                                 "Rollback authority remains with the deterministic Phase 16 rollback policy."),
            confidence=0.9,
            limitations="Explanation derives from the recorded rollback verification; it does not verify artifacts itself.",
            requires_human_review=False, query_type=query.query_type)

    def _missing(self, query: AgentQuery, kind: str) -> AgentOutput:
        return AgentOutput(
            agent_id=self.agent_id, agent_version=self.agent_version, query_id=query.query_id,
            input_evidence_refs=[], reasoning_summary=f"No structured {kind} was supplied.",
            recommendation="EXPLAIN", recommendation_text=f"Provide a structured {kind} record.",
            confidence=0.2, limitations="Missing evidence handled gracefully.",
            requires_human_review=False, query_type=query.query_type)
