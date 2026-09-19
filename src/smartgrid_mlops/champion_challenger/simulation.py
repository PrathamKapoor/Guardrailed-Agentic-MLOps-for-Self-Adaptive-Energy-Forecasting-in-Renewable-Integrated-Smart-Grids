"""Frozen champion-challenger scenarios CC01-CC06 and the governed promotion pipeline.

The pipeline is: evaluation -> promotion decision -> canary simulation ->
promotion (or canary rollback) -> post-promotion monitoring -> verified rollback.
Every step is deterministic and audited. Scenario fixtures are metadata-only
and explicitly labelled SIMULATION, mirroring the Phase 13 governance scenario
method; rollback verification uses preserved real model artifacts."""
from __future__ import annotations
from .canary import run_canary
from .evaluation import evaluate_challenger
from .policy import PromotionPolicy
from .promotion import decide
from .rollback import degradation_detected, execute_rollback, verify_restoration
from .schemas import ChallengerEvaluationContext

SCENARIO_IDS = ("CC01", "CC02", "CC03", "CC04", "CC05", "CC06")

SCENARIO_DESCRIPTIONS = {
    "CC01": "better challenger, valid governance -> APPROVE, canary pass, PROMOTED (simulation)",
    "CC02": "better challenger, invalid lineage -> REJECT",
    "CC03": "better challenger, benchmark gate fails -> REJECT",
    "CC04": "worse challenger -> REJECT",
    "CC05": "valid promotion followed by post-promotion degradation -> ROLLBACK_COMPLETED",
    "CC06": "rollback integrity failure (preserved artifact fingerprint mismatch) -> ROLLBACK_BLOCKED",
}

EXPECTED_OUTCOMES = {"CC01": "PROMOTED", "CC02": "REJECT", "CC03": "REJECT",
                     "CC04": "REJECT", "CC05": "ROLLBACK_COMPLETED", "CC06": "ROLLBACK_BLOCKED"}


def valid_context(**overrides) -> ChallengerEvaluationContext:
    """CC01-style fixture: better challenger with complete valid governance metadata,
    explicitly labelled SIMULATION with SIMULATION_POLICY approval."""
    fields = dict(challenger_id="SIM-CHAL-CC-VALID", reference_id="MLOPS-REF-LOAD-H24-V1",
                  target="load", simulation=True, registered=True, lineage_status="COMPLETE",
                  approval_state="APPROVED", approval_actor="SIMULATION_POLICY", policy_mode="SIMULATION",
                  benchmark_gate="BENCHMARK_GATE_PASS", statistical_evidence="REQUIRED_PASS",
                  reference_mae=100.0, challenger_mae=90.0, canary_regression_percent=-5.0)
    fields.update(overrides)
    return ChallengerEvaluationContext(**fields)


def scenario_context(scenario_id: str, *, protocol_hash: str) -> ChallengerEvaluationContext:
    common = dict(protocol_hash=protocol_hash)
    if scenario_id == "CC01":
        return valid_context(**common, challenger_id="SIM-CHAL-CC01")
    if scenario_id == "CC02":
        return valid_context(**common, challenger_id="SIM-CHAL-CC02", lineage_status="INCOMPLETE")
    if scenario_id == "CC03":
        return valid_context(**common, challenger_id="SIM-CHAL-CC03", benchmark_gate="BENCHMARK_GATE_FAIL")
    if scenario_id == "CC04":
        return valid_context(**common, challenger_id="SIM-CHAL-CC04", challenger_mae=105.0)
    if scenario_id == "CC05":
        return valid_context(**common, challenger_id="SIM-CHAL-CC05", post_promotion_regression_percent=4.2)
    if scenario_id == "CC06":
        return valid_context(**common, challenger_id="SIM-CHAL-CC06", post_promotion_regression_percent=4.2)
    raise ValueError(f"Unknown scenario {scenario_id}")


def run_pipeline(context: ChallengerEvaluationContext, policy: PromotionPolicy, *,
                 preservation=None, corrupted_preservation=None, lineage_nodes=None,
                 probe_features=None, emit_event=None,
                 expected_preservation_fingerprint: str | None = None) -> dict:
    """Deterministic promotion pipeline for one evaluation context."""
    evaluation = evaluate_challenger(context)
    if emit_event:
        emit_event("CHALLENGER_EVALUATED", context.challenger_id,
                   {"reference_id": context.reference_id, "target": context.target,
                    "challenger_mae": context.challenger_mae, "reference_mae": context.reference_mae,
                    "simulation": context.simulation})
    if emit_event:
        emit_event("PROMOTION_REQUESTED", context.challenger_id,
                   {"reference_id": context.reference_id, "policy_version": policy.version})
    decision = decide(context, policy)
    if emit_event:
        emit_event({"APPROVE": "PROMOTION_APPROVED", "REJECT": "PROMOTION_REJECTED",
                    "DEFER": "PROMOTION_DEFERRED"}[decision.decision], context.challenger_id,
                   {"reason_codes": decision.reason_codes, "policy_version": policy.version})
    result = {"scenario_id": context.challenger_id, "challenger_id": context.challenger_id,
              "reference_id": context.reference_id, "target": context.target,
              "decision": decision.decision, "reason_codes": decision.reason_codes,
              "evaluation": evaluation, "decision_record": decision.to_dict(),
              "canary": None, "promoted": False, "rollback": None, "outcome": decision.decision}
    if decision.decision != "APPROVE":
        return result
    canary = run_canary(context, policy)
    if emit_event:
        emit_event("CANARY_STARTED", context.challenger_id,
                   {"max_allowed_regression_percent": canary.max_allowed_regression_percent})
    result["canary"] = canary.to_dict()
    if not canary.passed:
        if emit_event:
            emit_event("CANARY_FAILED", context.challenger_id,
                       {"canary_regression_percent": canary.canary_regression_percent})
        result["outcome"] = "CANARY_FAILED_ROLLED_BACK"
        return result
    if emit_event:
        emit_event("MODEL_PROMOTED", context.challenger_id,
                   {"reference_id": context.reference_id, "simulation": True,
                    "policy_fingerprint": policy.promotion_policy_fingerprint})
    result["promoted"] = True
    result["outcome"] = "PROMOTED"
    triggered, regression, threshold = degradation_detected(context.post_promotion_regression_percent, policy)
    if not triggered:
        return result
    if emit_event:
        emit_event("ROLLBACK_REQUESTED", context.challenger_id,
                   {"degradation_percent": regression, "threshold_percent": threshold})
    record = corrupted_preservation if corrupted_preservation is not None else preservation
    if record is None:
        raise ValueError("rollback requires a preserved previous model")
    verification = verify_restoration(record, expected_fingerprint=expected_preservation_fingerprint,
                                      lineage_nodes=lineage_nodes, probe_features=probe_features)
    rollback = execute_rollback(promoted_model_id=context.challenger_id, previous=record,
                                regression_percent=regression, threshold_percent=threshold,
                                verification=verification)
    if emit_event:
        emit_event(rollback.outcome, context.challenger_id,
                   {"previous_model_id": record.model_id, "failed_checks": verification["failed"]})
    result["rollback"] = rollback.to_dict()
    result["outcome"] = rollback.outcome
    return result
