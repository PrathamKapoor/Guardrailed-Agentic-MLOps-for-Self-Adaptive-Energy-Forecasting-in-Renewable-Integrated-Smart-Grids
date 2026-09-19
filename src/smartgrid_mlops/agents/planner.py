"""Planner: routes structured queries to bounded specialist agents."""
from __future__ import annotations
from pathlib import Path
from .base import LocalRuleBackend
from .drift_agent import DriftAnalysisAgent
from .evidence_agent import EvidenceRetrievalAgent
from .governance_agent import GovernanceExplanationAgent
from .retraining_agent import RetrainingExplanationAgent
from .report_agent import ReportGenerationAgent
from .schemas import QUERY_TYPES


class Planner:
    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)
        backend = LocalRuleBackend()
        self.agents = {
            "DRIFT_ANALYSIS_AGENT": DriftAnalysisAgent(backend),
            "RETRAINING_EXPLANATION_AGENT": RetrainingExplanationAgent(backend),
            "GOVERNANCE_EXPLANATION_AGENT": GovernanceExplanationAgent(backend),
            "REPORT_GENERATION_AGENT": ReportGenerationAgent(backend),
            "EVIDENCE_RETRIEVAL_AGENT": EvidenceRetrievalAgent(self.project_root, backend),
        }

    def route(self, query_type: str):
        agent_id = QUERY_TYPES.get(query_type)
        if agent_id is None:
            raise ValueError(f"UNKNOWN_AGENT_QUERY_TYPE: {query_type}")
        return self.agents[agent_id]
