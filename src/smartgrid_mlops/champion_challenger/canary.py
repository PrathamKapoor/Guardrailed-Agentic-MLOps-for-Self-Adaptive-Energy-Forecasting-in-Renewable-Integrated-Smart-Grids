"""Deterministic canary SIMULATION. No deployment exists in Phase 16.

Lifecycle (simulation-scoped, mapped onto the Phase 13 state machine):
REGISTERED_CHALLENGER -> APPROVED_FOR_CANARY -> CANARY_ACTIVE -> ACTIVE (promoted)
or CANARY failure -> challenger rolled back before activation, reference unchanged."""
from __future__ import annotations
from .policy import PromotionPolicy
from .schemas import CanaryOutcome, ChallengerEvaluationContext


def run_canary(context: ChallengerEvaluationContext, policy: PromotionPolicy) -> CanaryOutcome:
    """Guardrail: challenger canary-window MAE regression vs the reference must not
    exceed the frozen maximum. The canary metric is the frozen canary evidence of
    the evaluation context (declared fixture or recorded matched-window result)."""
    max_regression = float(policy.document["canary_policy"]["max_mae_regression_percent"])
    regression = float(context.canary_regression_percent)
    passed = regression <= max_regression
    return CanaryOutcome(
        challenger_id=context.challenger_id, passed=passed,
        canary_regression_percent=regression, max_allowed_regression_percent=max_regression,
        reason_code="CANARY_PASSED" if passed else "CANARY_FAILED")
