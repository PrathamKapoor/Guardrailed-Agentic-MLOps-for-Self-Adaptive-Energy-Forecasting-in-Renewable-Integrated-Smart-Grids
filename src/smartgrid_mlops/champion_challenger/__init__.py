"""Deterministic champion-challenger evaluation, governed promotion, and rollback (Phase 16).

Promotion is never triggered by superior MAE alone: every promotion passes a
frozen deterministic policy (registration, lineage, fingerprints, protocol,
metadata, evaluation, performance, benchmark, statistics, approval) followed by
a canary simulation; rollback restores a preserved previous model after
verified degradation. All promotion activity in Phase 16 is SIMULATION and is
labelled as such; no deployment exists.
"""
from .schemas import ChallengerEvaluationContext, PromotionDecision, CanaryOutcome, RollbackRecord
from .policy import PromotionPolicy

__all__ = ["ChallengerEvaluationContext", "PromotionDecision", "CanaryOutcome", "RollbackRecord", "PromotionPolicy"]
