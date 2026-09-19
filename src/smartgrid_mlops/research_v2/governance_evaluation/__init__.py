"""Stage 12: Evidence-to-governance evaluation.

Translates Stage 10 and Stage 11 research evidence into the EXISTING
deterministic governance system. This is a TRANSLATION layer only;
it does NOT promote a model, deploy a model, or modify any
lifecycle state. The only allowed mutation is the append-only
audit JSONL emission via `smartgrid_mlops.governance.audit.audit_decision`.
"""
from .evidence import (
    EvidenceClass, NormalizedEvidence, normalize_evidence,
    read_stage_10_evidence, read_stage_11_per_fold, read_stage_11_summary,
)
from .adapter import (
    DEFAULT_AUDIT_PATH, build_candidate_context, build_transition_request,
    evaluate_candidate,
)
from .runner import (
    V2_ROOT, STAGE_10_DIR, STAGE_11_PER_FOLD, STAGE_11_SUMMARY,
    PHASE_13_POLICY, run_governance_evaluation,
)

__all__ = [
    "DEFAULT_AUDIT_PATH",
    "EvidenceClass",
    "NormalizedEvidence",
    "PHASE_13_POLICY",
    "STAGE_10_DIR",
    "STAGE_11_PER_FOLD",
    "STAGE_11_SUMMARY",
    "V2_ROOT",
    "build_candidate_context",
    "build_transition_request",
    "evaluate_candidate",
    "normalize_evidence",
    "read_stage_10_evidence",
    "read_stage_11_per_fold",
    "read_stage_11_summary",
    "run_governance_evaluation",
]
