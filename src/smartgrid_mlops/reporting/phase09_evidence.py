"""Single, explicit eligibility policy for Phase 9 research reporting.

This module deliberately does not infer status from a path.  Callers must
attach an evidence status to every candidate record before selection.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

OFFICIAL_EVIDENCE_STATUSES = frozenset({"VALID"})
VALID_NEURAL_FRAMEWORK = "pytorch"
VALID_NEURAL_IMPLEMENTATION = "PYTORCH_MLP_V1"


def is_official_evidence(record: Mapping[str, Any]) -> bool:
    """Return whether a record is eligible for official research outputs."""
    return record.get("evidence_status") in OFFICIAL_EVIDENCE_STATUSES


def is_valid_neural_evidence(record: Mapping[str, Any]) -> bool:
    """Apply the Phase 8 identity requirement in addition to status."""
    return (
        is_official_evidence(record)
        and str(record.get("framework", "")).lower() == VALID_NEURAL_FRAMEWORK
        and record.get("implementation_id") == VALID_NEURAL_IMPLEMENTATION
    )


def select_official_evidence(
    records: Iterable[Mapping[str, Any]], *, neural_only: bool = False
) -> tuple[list[Mapping[str, Any]], list[dict[str, Any]]]:
    """Select valid records and expose practical, non-mutating rejection reasons."""
    included: list[Mapping[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for record in records:
        eligible = is_valid_neural_evidence(record) if neural_only else is_official_evidence(record)
        if eligible:
            included.append(record)
            continue
        if record.get("evidence_status") != "VALID":
            reason = f"evidence_status={record.get('evidence_status')!r} is not VALID"
        elif neural_only:
            reason = "neural identity must be framework=pytorch and implementation_id=PYTORCH_MLP_V1"
        else:
            reason = "not eligible"
        rejected.append({"record": dict(record), "reason": reason})
    return included, rejected
