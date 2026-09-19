"""Drift analysis agent: explains Phase 14/15 drift evidence.

Cannot change thresholds or approve retraining; output is advisory only."""
from __future__ import annotations
from .base import Agent
from .schemas import AgentOutput, AgentQuery

SEVERITY_EXPLANATIONS = {
    "NONE": "no detector exceeded its calibrated threshold",
    "WATCH": "a single detector exceeded its calibrated threshold; observation only",
    "WARNING": "multiple detectors or a moderate excess exceeded thresholds",
    "CRITICAL": "a large excess or data-quality failure exceeded thresholds",
}

POSSIBLE_CAUSES = {
    "FEATURE_DRIFT": "input distribution shift in lag features (demand or generation regime change)",
    "PREDICTION_DRIFT": "model output distribution moved relative to its calibration period",
    "PERFORMANCE_DRIFT": "forecast errors deteriorated against observed labels",
    "ERROR_DISTRIBUTION_DRIFT": "the error distribution changed shape, not just level",
    "DATA_QUALITY": "upstream data-quality failure (missingness, schema, or non-finite values)",
}


class DriftAnalysisAgent(Agent):
    agent_id = "DRIFT_ANALYSIS_AGENT"
    agent_version = "1.0.0"

    def analyze(self, query: AgentQuery) -> AgentOutput:
        event = query.payload.get("drift_event")
        refs = [str(x) for x in query.payload.get("evidence_refs", [])]
        if not event:
            return self._missing(query)
        detectors = event.get("triggered", [])
        severity = event.get("severity", "UNKNOWN")
        target = event.get("target", "unknown")
        causes = [POSSIBLE_CAUSES[d] for d in detectors if d in POSSIBLE_CAUSES]
        inconsistent = severity == "NONE" and bool(detectors)
        summary = (f"Drift alert on target '{target}' (scenario {event.get('scenario_id', 'unknown')}) "
                   f"reached severity {severity}: {SEVERITY_EXPLANATIONS.get(severity, 'severity semantics unavailable')}. "
                   f"Detectors triggered: {', '.join(detectors) if detectors else 'none recorded'}. "
                   f"Signal values: {json_compact(event.get('signal_values', {}))}. "
                   f"Possible causes: {'; '.join(causes) if causes else 'undetermined from available evidence'}."
                   + (" INCONSISTENT EVIDENCE: severity NONE conflicts with triggered detectors; flagged for review."
                      if inconsistent else ""))
        return AgentOutput(
            agent_id=self.agent_id, agent_version=self.agent_version, query_id=query.query_id,
            input_evidence_refs=refs, reasoning_summary=summary,
            recommendation="INVESTIGATE",
            recommendation_text=("Verify upstream data pipelines, compare pre-onset and current windows for the "
                                 "affected target, and review data-quality status before any governance request. "
                                 "This alert is observational evidence and cannot itself trigger retraining."),
            confidence=0.5 if inconsistent else (0.9 if refs else 0.6),
            limitations=("Explanations are rule-based mappings from detector output; they do not establish causation "
                         "and cannot modify thresholds or approve retraining."),
            requires_human_review=True, query_type=query.query_type)

    def _missing(self, query: AgentQuery) -> AgentOutput:
        return AgentOutput(
            agent_id=self.agent_id, agent_version=self.agent_version, query_id=query.query_id,
            input_evidence_refs=[], reasoning_summary="No drift event was supplied; nothing to explain.",
            recommendation="EXPLAIN", recommendation_text="Provide a structured DriftEvent to obtain an explanation.",
            confidence=0.2, limitations="Missing-evidence handling is graceful; no fabricated explanation is produced.",
            requires_human_review=False, query_type=query.query_type)


def json_compact(value) -> str:
    import json
    return json.dumps(value, sort_keys=True)
