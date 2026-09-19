"""Deterministic, governance-controlled retraining and challenger generation (Phase 15).

Drift evidence is observational; retraining requires an independently evaluated
deterministic policy; successful challengers terminate at REGISTERED_CHALLENGER
and never replace the reference automatically.
"""
from .schemas import RetrainingRequest, RetrainingDecision, GateOutcome, ChallengerRecord
from .policy import RetrainingPolicy

__all__ = ["RetrainingRequest", "RetrainingDecision", "GateOutcome", "ChallengerRecord", "RetrainingPolicy"]
