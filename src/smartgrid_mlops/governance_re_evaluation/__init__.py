"""Stage 14: governance-compatible candidate re-evaluation.

This package re-evaluates the seven Stage 13 candidate packages
through the EXISTING frozen Phase 13 GovernanceEngine. It is a
governance EVALUATION stage, not a governance EXECUTION stage.
The only allowed mutation is the append-only audit JSONL
emission via the existing `smartgrid_mlops.governance.audit.audit_decision`
helper. No model is promoted, deployed, retrained, rolled back, or
otherwise lifecycle-mutated by Stage 14.

The Stage 14 layer is read-only with respect to the v1 tree and the
Stage 13 packages. It writes only under
`artifacts/v2/governance_re_evaluation/`.
"""
from .loader import (
    LoadedPackage, PackageIntegrityError, STAGE_13_ROOT,
    REQUIRED_FILES, list_candidate_ids, load_package, load_all_packages,
    V2_ROOT,
)
from .evaluator import (
    STAGE_14_ROOT, GATE_RESULTS_DIR, STAGE_14_AUDIT_PATH,
)
from .adapter import (
    AdaptedCandidate, EvidenceGap, DEFAULT_TRANSITION,
    PASS_THROUGH_BENCHMARK, adapt,
)
from .evaluator import (
    CandidateDecision, STAGE_14_ROOT, GATE_RESULTS_DIR,
    STAGE_14_AUDIT_PATH, evaluate_candidate, run_reevaluation,
)

__all__ = [
    "AdaptedCandidate",
    "CandidateDecision",
    "DEFAULT_TRANSITION",
    "EvidenceGap",
    "GATE_RESULTS_DIR",
    "LoadedPackage",
    "PASS_THROUGH_BENCHMARK",
    "PackageIntegrityError",
    "REQUIRED_FILES",
    "STAGE_13_ROOT",
    "STAGE_14_AUDIT_PATH",
    "STAGE_14_ROOT",
    "adapt",
    "evaluate_candidate",
    "list_candidate_ids",
    "load_all_packages",
    "load_package",
    "run_reevaluation",
]
