"""Shared evidence policy delegates Phase 9 neural identity rules to the existing filter."""
from smartgrid_mlops.reporting.phase09_evidence import is_official_evidence, is_valid_neural_evidence


def evidence_route(record: dict) -> str:
    status = record.get("evidence_status")
    if status == "INVALIDATED":
        return "AUDIT_ONLY"
    if status == "NON_EVIDENCE_SMOKE":
        return "EXCLUDED"
    if str(record.get("model_family", record.get("model", ""))).lower() == "mlp":
        return "OFFICIAL" if is_valid_neural_evidence(record) else "REJECTED"
    return "OFFICIAL" if is_official_evidence(record) else "REJECTED"
