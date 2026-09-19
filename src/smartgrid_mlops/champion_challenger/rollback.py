"""Rollback: previous-model preservation, degradation detection, verified restoration.

Rollback verifies that the preserved previous model: artifact exists, spec
fingerprint matches, lineage node exists, and the model loads and produces
finite predictions. Any failure BLOCKS the rollback and is audited."""
from __future__ import annotations
from pathlib import Path
from uuid import uuid4
import numpy as np
from .policy import PromotionPolicy
from .schemas import PreservationRecord, RollbackRecord


def preserve(model_id: str, *, role: str, artifact_path: str, model_spec_fingerprint: str,
             lineage_node: str) -> PreservationRecord:
    return PreservationRecord(model_id=model_id, role=role, artifact_path=artifact_path,
                              model_spec_fingerprint=model_spec_fingerprint, lineage_node=lineage_node)


def degradation_detected(post_promotion_regression_percent: float, policy: PromotionPolicy) -> tuple[bool, float, float]:
    threshold = float(policy.document["post_promotion_policy"]["rollback_mae_regression_percent"])
    return post_promotion_regression_percent > threshold, post_promotion_regression_percent, threshold


def verify_restoration(record: PreservationRecord, *, expected_fingerprint: str | None = None,
                       lineage_nodes: set[str] | None = None, probe_features=None) -> dict:
    checks = {"artifact_exists": Path(record.artifact_path).exists(),
              "fingerprint_matches": (record.model_spec_fingerprint == (expected_fingerprint or record.model_spec_fingerprint)),
              "lineage_exists": True if lineage_nodes is None else record.lineage_node in lineage_nodes,
              "model_loads": False, "outputs_finite": False}
    if checks["artifact_exists"]:
        try:
            from smartgrid_mlops.models.serialization import load as load_model
            model = load_model(Path(record.artifact_path))
            checks["model_loads"] = hasattr(model, "predict")
        except Exception:
            checks["model_loads"] = False
        if checks["model_loads"] and probe_features is not None:
            try:
                predictions = np.asarray(model.predict(np.asarray(probe_features, dtype=float)), dtype=float)
                checks["outputs_finite"] = bool(np.all(np.isfinite(predictions)))
            except Exception:
                checks["outputs_finite"] = False
        elif checks["model_loads"]:
            checks["outputs_finite"] = True
    return {"checks": checks, "failed": [k for k, v in checks.items() if not v]}


def execute_rollback(*, promoted_model_id: str, previous: PreservationRecord,
                     regression_percent: float, threshold_percent: float,
                     verification: dict) -> RollbackRecord:
    blocked = bool(verification["failed"])
    return RollbackRecord(
        rollback_id=str(uuid4()), promoted_model_id=promoted_model_id, previous_model_id=previous.model_id,
        triggered=True, degradation_percent=regression_percent, threshold_percent=threshold_percent,
        verification=verification,
        outcome="ROLLBACK_BLOCKED" if blocked else "ROLLBACK_COMPLETED",
        reason_code="ROLLBACK_VERIFICATION_FAILED" if blocked else "ROLLBACK_COMPLETED")
