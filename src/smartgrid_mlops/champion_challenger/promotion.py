"""Deterministic promotion gates. Improved MAE alone is never sufficient."""
from __future__ import annotations
from uuid import uuid4
from .policy import PromotionPolicy
from .schemas import ChallengerEvaluationContext, GateOutcome, PromotionDecision

APPROVED_STATUSES = ("BENCHMARK_GATE_PASS",)
ACCEPTED_STATISTICAL = ("REQUIRED_PASS", "NOT_REQUIRED")


def _outcome(gate, passed, reason, ok, fail):
    return GateOutcome(gate, passed, None if passed else reason, ok if passed else fail)


def _policy_version_gate(c: ChallengerEvaluationContext, p: PromotionPolicy):
    passed = (c.claimed_policy_id in (None, p.policy_id)
              and c.claimed_policy_version in (None, p.version)
              and c.claimed_policy_checksum in (None, p.checksum))
    return _outcome("POLICY_VERSION_GATE", passed, "POLICY_VERSION_MISMATCH",
                    "Promotion policy identity matches.", "Claimed promotion policy identity does not match the frozen policy.")


def _final_test_gate(c: ChallengerEvaluationContext, p: PromotionPolicy):
    return _outcome("FINAL_TEST_GATE", not c.requests_final_test_access, "FINAL_TEST_POLICY_VIOLATION",
                    "No final-test access requested.", "Phase 16 forbids final-test data in promotion decisions.")


def _registration_gate(c: ChallengerEvaluationContext, p: PromotionPolicy):
    return _outcome("REGISTRATION_GATE", c.registered, "CHALLENGER_NOT_REGISTERED",
                    "Challenger is REGISTERED_CHALLENGER in the Phase 15 registry.",
                    "Challenger is not registered in the challenger registry.")


def _lineage_gate(c: ChallengerEvaluationContext, p: PromotionPolicy):
    return _outcome("LINEAGE_GATE", c.lineage_status == "COMPLETE", "LINEAGE_INCOMPLETE",
                    "Challenger lineage is complete.", "Challenger lineage is incomplete.")


def _model_fingerprint_gate(c: ChallengerEvaluationContext, p: PromotionPolicy):
    return _outcome("MODEL_FINGERPRINT_GATE", c.actual_model_fingerprint == c.expected_model_fingerprint,
                    "MODEL_FINGERPRINT_MISMATCH",
                    "Model specification fingerprint matches the frozen reference specification.",
                    "Model specification fingerprint differs from the frozen reference specification.")


def _feature_fingerprint_gate(c: ChallengerEvaluationContext, p: PromotionPolicy):
    return _outcome("FEATURE_FINGERPRINT_GATE", c.actual_feature_fingerprint == c.expected_feature_fingerprint,
                    "FEATURE_FINGERPRINT_MISMATCH",
                    "Feature fingerprint matches the frozen specification.",
                    "Feature fingerprint differs from the frozen specification.")


def _protocol_gate(c: ChallengerEvaluationContext, p: PromotionPolicy):
    return _outcome("PROTOCOL_GATE", c.protocol_hash in p.document["accepted_protocol_hashes"], "PROTOCOL_MISMATCH",
                    "Protocol hash is accepted by the frozen promotion policy.",
                    "Protocol hash is not accepted by the frozen promotion policy.")


def _metadata_gate(c: ChallengerEvaluationContext, p: PromotionPolicy):
    return _outcome("METADATA_GATE", c.metadata_complete, "METADATA_INCOMPLETE",
                    "Required challenger metadata is complete.",
                    "Required challenger metadata is missing.")


def _evaluation_gate(c: ChallengerEvaluationContext, p: PromotionPolicy):
    minimum = int(p.document["performance_policy"].get("minimum_matched_rows", 1))
    passed = c.evaluation_completed and c.matched_evaluation_rows >= minimum
    return _outcome("EVALUATION_GATE", passed, "EVALUATION_INCOMPLETE",
                    f"Matched evaluation complete ({c.matched_evaluation_rows} rows >= {minimum}).",
                    "Matched evaluation is missing or below the frozen minimum.")


def _performance_gate(c: ChallengerEvaluationContext, p: PromotionPolicy):
    margin = float(p.document["performance_policy"]["minimum_relative_mae_improvement_percent"])
    improvement = 100.0 * (c.reference_mae - c.challenger_mae) / c.reference_mae if c.reference_mae else 0.0
    passed = improvement > margin
    return _outcome("PERFORMANCE_GATE", passed, "CHALLENGER_NOT_BETTER",
                    f"Challenger MAE strictly improves the reference by {improvement:.3f}% (> {margin}%).",
                    f"Challenger MAE does not strictly improve the reference ({improvement:.3f}% <= {margin}%).")


def _benchmark_gate(c: ChallengerEvaluationContext, p: PromotionPolicy):
    passed = c.benchmark_gate in APPROVED_STATUSES
    return _outcome("BENCHMARK_GATE", passed, "BENCHMARK_REQUIREMENT_NOT_SATISFIED",
                    "Challenger satisfies the frozen development benchmark requirement.",
                    "Challenger does not satisfy the frozen development benchmark requirement "
                    "(synthetic-scenario superiority over the reference is not benchmark evidence).")


def _statistical_gate(c: ChallengerEvaluationContext, p: PromotionPolicy):
    passed = c.statistical_evidence in p.document["statistical_evidence_policy"]["accepted_statuses"]
    return _outcome("STATISTICAL_GATE", passed, "STATISTICAL_EVIDENCE_INSUFFICIENT",
                    "Statistical evidence policy is satisfied.",
                    "Statistical evidence fails or is insufficient for promotion.")


def _approval_gate(c: ChallengerEvaluationContext, p: PromotionPolicy):
    if c.approval_state == "REJECTED":
        return _outcome("APPROVAL_GATE", False, "APPROVAL_REJECTED",
                        "", "Recorded approval was rejected.")
    if c.approval_state != "APPROVED":
        return _outcome("APPROVAL_GATE", False, "APPROVAL_REQUIRED",
                        "", "Explicit approval is required before promotion; none is recorded.")
    actor_ok = c.approval_actor == p.document["approval_policy"]["simulation_actor"] and c.policy_mode == "SIMULATION"
    return _outcome("APPROVAL_GATE", actor_ok, "APPROVAL_REQUIRED",
                    "Explicitly labelled SIMULATION_POLICY approval is recorded.",
                    "No acceptable explicit approval evidence is present.")


GATES = (_policy_version_gate, _final_test_gate, _registration_gate, _lineage_gate,
         _model_fingerprint_gate, _feature_fingerprint_gate, _protocol_gate, _metadata_gate,
         _evaluation_gate, _performance_gate, _benchmark_gate, _statistical_gate, _approval_gate)


def decide(context: ChallengerEvaluationContext, policy: PromotionPolicy) -> PromotionDecision:
    outcomes = [fn(context, policy) for fn in GATES]
    failed = [o for o in outcomes if not o.passed]
    defer_only = [o for o in failed if o.reason_code == "APPROVAL_REQUIRED"]
    if any(o.reason_code != "APPROVAL_REQUIRED" for o in failed):
        decision = "REJECT"; reasons = [o.reason_code for o in failed if o.reason_code != "APPROVAL_REQUIRED"]
    elif defer_only:
        decision = "DEFER"; reasons = ["APPROVAL_REQUIRED"]
    else:
        decision = "APPROVE"; reasons = ["PROMOTION_APPROVED"]
    metrics = {"reference_mae": context.reference_mae, "challenger_mae": context.challenger_mae,
               "matched_evaluation_rows": context.matched_evaluation_rows,
               "relative_mae_improvement_percent": (100.0 * (context.reference_mae - context.challenger_mae)
                                                    / context.reference_mae) if context.reference_mae else 0.0,
               "benchmark_gate": context.benchmark_gate}
    return PromotionDecision(
        decision_id=str(uuid4()), challenger_id=context.challenger_id,
        reference_id=context.reference_id, target=context.target, decision=decision,
        reason_codes=reasons, gate_results=[o.to_dict() for o in outcomes], metrics=metrics,
        policy_id=policy.policy_id, policy_version=policy.version, policy_checksum=policy.checksum,
        promotion_policy_fingerprint=policy.promotion_policy_fingerprint, simulation=context.simulation)


def is_unsafe_attempt(context: ChallengerEvaluationContext, decision: PromotionDecision) -> bool:
    """Frozen definition: a promotion request that appears superior (challenger MAE
    strictly better than the reference) while the governed decision is not APPROVE."""
    return context.challenger_mae < context.reference_mae and decision.decision != "APPROVE"
