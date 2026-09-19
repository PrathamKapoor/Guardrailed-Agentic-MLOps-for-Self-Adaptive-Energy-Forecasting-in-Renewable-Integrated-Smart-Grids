"""Challenger admission checks and registration.

Terminal Phase 15 state is REGISTERED_CHALLENGER with promotion_eligible=false.
Promotion evaluation belongs to Phase 16 champion-challenger governance."""
from __future__ import annotations
import numpy as np
from .schemas import ChallengerRecord

REGISTRATION_CHECKS = ("training_completed", "evidence_valid", "lineage_complete",
                       "feature_fingerprint_valid", "model_specification_valid",
                       "training_dataset_fingerprint_present", "evaluation_complete",
                       "outputs_finite", "no_unresolved_deviation", "final_test_policy_respected")


def admission_checks(*, training_completed: bool, evidence_status: str, lineage_status: str,
                     actual_feature_fingerprint: str, expected_feature_fingerprint: str,
                     model_spec_fingerprint: str, parent_spec_fingerprint: str,
                     training_dataset_fingerprint: str | None, evaluation: dict | None,
                     predictions_finite: bool, unresolved_deviation: bool,
                     final_test_accessed: bool) -> dict:
    checks = {
        "training_completed": training_completed,
        "evidence_valid": evidence_status == "VALID",
        "lineage_complete": lineage_status == "COMPLETE",
        "feature_fingerprint_valid": actual_feature_fingerprint == expected_feature_fingerprint,
        "model_specification_valid": model_spec_fingerprint == parent_spec_fingerprint,
        "training_dataset_fingerprint_present": bool(training_dataset_fingerprint),
        "evaluation_complete": evaluation is not None and evaluation.get("evaluation_rows", 0) > 0,
        "outputs_finite": bool(predictions_finite),
        "no_unresolved_deviation": not unresolved_deviation,
        "final_test_policy_respected": not final_test_accessed,
    }
    failed = [name for name in REGISTRATION_CHECKS if not checks[name]]
    return {"checks": checks, "failed": failed, "decision": "REGISTERED_CHALLENGER" if not failed else "REJECTED"}


def build_challenger_record(*, challenger_id: str, target: str, parent_reference_id: str, scenario: str,
                            model_family: str, feature_set: str, model_spec_fingerprint: str,
                            model_instance_fingerprint: str, training_dataset_fingerprint: str,
                            training_cutoff: str, evaluation: dict | None,
                            evidence_refs: list[str], mlflow_run_id: str | None,
                            registry_state: str, promotion_eligible: bool) -> ChallengerRecord:
    reference_mae = evaluation["reference"]["MAE"] if evaluation else None
    challenger_mae = evaluation["challenger"]["MAE"] if evaluation else None
    gain = None
    if reference_mae and challenger_mae is not None:
        gain = 100.0 * (reference_mae - challenger_mae) / reference_mae
    return ChallengerRecord(
        challenger_id=challenger_id, target=target, parent_reference=parent_reference_id,
        scenario=scenario, model_family=model_family, feature_set=feature_set,
        model_spec_fingerprint=model_spec_fingerprint,
        model_instance_fingerprint=model_instance_fingerprint,
        training_dataset_fingerprint=training_dataset_fingerprint, training_cutoff=training_cutoff,
        evaluation_window_start=evaluation["window_start"] if evaluation else "",
        evaluation_window_end=evaluation["window_end"] if evaluation else "",
        reference_mae=reference_mae, challenger_mae=challenger_mae,
        adaptation_gain_percent=gain, registry_state=registry_state,
        promotion_eligible=promotion_eligible, evidence_refs=evidence_refs,
        mlflow_run_id=mlflow_run_id)


def outputs_finite(predictions) -> bool:
    return bool(np.all(np.isfinite(np.asarray(predictions, dtype=float))))
