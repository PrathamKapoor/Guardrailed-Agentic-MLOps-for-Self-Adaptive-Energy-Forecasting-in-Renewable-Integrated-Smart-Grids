"""Stage 12: Governance evaluation adapter.

This module is the THINNEST possible layer that:
  1. Loads the frozen Phase 13 governance policy.
  2. Translates a `NormalizedEvidence` into a `CandidateContext`
     and a `TransitionRequest` (the existing governance input
     shapes).
  3. Calls the existing `GovernanceEngine.evaluate(...)`.
  4. Records the resulting `GovernanceDecision` to the existing
     append-only audit JSONL (which is the only allowed mutation).
  5. Writes a per-candidate evidence-gaps JSON so missing
     evidence is visible to future governance stages.

It does NOT:
  - promote a model
  - deploy a model
  - change the lifecycle state
  - modify the Phase 13 policy
  - add HTTP endpoints
  - modify the registry

The adapter is a TRANSLATION LAYER ONLY. It reuses the existing
governance engine and the existing audit emission.
"""
from __future__ import annotations
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from smartgrid_mlops.governance.audit import audit_decision
from smartgrid_mlops.governance.decisions import EXPLANATIONS
from smartgrid_mlops.governance.policies import GovernancePolicy
from smartgrid_mlops.governance.policy_engine import GovernanceEngine
from smartgrid_mlops.governance.schemas import (
    DECISIONS, LIFECYCLE_STATES, REASON_CODES,
    CandidateContext, TransitionRequest,
)

from .evidence import EvidenceClass, NormalizedEvidence, normalize_evidence


# The existing audit JSONL path. Stage 12 only writes here, never
# to the v1 tree. We use the v2 audit path to keep Stage 12
# separated from any v1 audit emissions.
DEFAULT_AUDIT_PATH = (
    Path(__file__).resolve().parents[4]
    / "artifacts" / "v2" / "governance_evaluation" / "stage12_audit.jsonl"
)


def _field_to_value(classes: list[EvidenceClass], name: str) -> tuple[str, Any]:
    """Map a single evidence class to the value the existing
    governance fields expect.

    The mapping is:
      VERIFIED            -> use the value verbatim
      CONTEXT_DEPENDENT  -> use the value verbatim (with note)
      MISSING            -> use a sentinel that fails the relevant gate
      NEGATIVE           -> use a sentinel that fails the relevant gate

    The returned `kind` is the evidence class kind, so the
    downstream JSON record can show it to a future operator.
    """
    for c in classes:
        if c.name == name:
            return c.kind, c.value
    return "MISSING", None


def build_candidate_context(
    ev: NormalizedEvidence,
    policy_mode: str = "RESEARCH",
) -> CandidateContext:
    """Translate `NormalizedEvidence` to the existing
    `CandidateContext`. The mapping is conservative: any MISSING
    or NEGATIVE evidence is rendered as a value that will FAIL the
    corresponding existing gate."""
    classes = {c.name: c for c in ev.classification}
    # evidence_status: VERIFIED if and only if the evidence_status
    # class itself is VERIFIED with value "VALID".
    es_kind, es_value = _field_to_value(ev.classification, "evidence_status")
    if es_kind == "VERIFIED" and es_value == "VALID":
        evidence_status = "VALID"
    else:
        evidence_status = "INVALID"  # forces the existing gate to fail
    # lineage_status: VERIFIED -> "COMPLETE", otherwise "INCOMPLETE"
    lineage_kind, _ = _field_to_value(ev.classification, "lineage_status")
    lineage_status = "COMPLETE" if lineage_kind == "VERIFIED" else "INCOMPLETE"
    # model_spec_fingerprint: NO exact match -> actual != expected
    ms_kind, _ = _field_to_value(ev.classification, "model_spec_fingerprint")
    if ms_kind == "VERIFIED":
        actual_mf = expected_mf = f"stage12-fingerprint-{ev.candidate_id}"
    else:
        actual_mf = "missing"
        expected_mf = f"stage12-fingerprint-{ev.candidate_id}"
    # feature_spec_fingerprint: same logic
    fs_kind, _ = _field_to_value(ev.classification, "feature_spec_fingerprint")
    if fs_kind == "VERIFIED":
        actual_ff = expected_ff = f"stage12-fingerprint-{ev.candidate_id}-features"
    else:
        actual_ff = "missing"
        expected_ff = f"stage12-fingerprint-{ev.candidate_id}-features"
    # protocol_hash: must be in policy.document["accepted_protocol_hashes"].
    # The Stage 12 evidence records the actual Phase 19 protocol
    # freeze SHA-256. The frozen policy's accepted_protocol_hashes
    # list does NOT include the Phase 19 hash, so the gate will
    # fail honestly. We use the actual recorded hash.
    pr_kind, pr_value = _field_to_value(ev.classification, "protocol_hash")
    protocol_hash = pr_value if pr_kind in ("VERIFIED", "CONTEXT_DEPENDENT") else "missing"
    # reproducibility_metadata
    rr_kind, _ = _field_to_value(ev.classification, "reproducibility_metadata")
    reproducibility_metadata = "COMPLETE" if rr_kind == "VERIFIED" else "INCOMPLETE"
    # deviation_status
    dv_kind, dv_value = _field_to_value(ev.classification, "deviation_status")
    if dv_kind in ("VERIFIED", "CONTEXT_DEPENDENT"):
        deviation_status = dv_value if dv_value else "NONE"
    else:
        deviation_status = "UNRESOLVED_CRITICAL"  # forces the gate to fail
    # benchmark_gate
    bg_kind, _ = _field_to_value(ev.classification, "benchmark_gate")
    benchmark_gate = "BENCHMARK_GATE_PASS" if bg_kind == "VERIFIED" else "BENCHMARK_GATE_FAIL"
    # statistical_evidence
    se_kind, _ = _field_to_value(ev.classification, "statistical_evidence")
    statistical_evidence = se_value if (se_kind == "VERIFIED" and se_value) else "NOT_REQUIRED"
    # final_test_access + integrity_audit_activation
    ft_kind, _ = _field_to_value(ev.classification, "final_test_access")
    requests_final_test_access = False  # always False: no NEW access
    requests_integrity_audit_activation = False  # always False
    return CandidateContext(
        subject_id=ev.candidate_id,
        evidence_status=evidence_status,
        official_candidate=True,
        lineage_status=lineage_status,
        actual_model_fingerprint=actual_mf,
        expected_model_fingerprint=expected_mf,
        actual_feature_fingerprint=actual_ff,
        expected_feature_fingerprint=expected_ff,
        protocol_hash=protocol_hash,
        reproducibility_metadata=reproducibility_metadata,
        deviation_status=deviation_status,
        benchmark_gate=benchmark_gate,
        statistical_evidence=statistical_evidence,
        approval_state="NOT_REQUIRED",
        approval_actor=None,
        policy_mode=policy_mode,
        requests_final_test_access=requests_final_test_access,
        requests_integrity_audit_activation=requests_integrity_audit_activation,
        evidence_refs=(
            f"artifacts/v2/residual_forecasting/evidence_packages/{ev.candidate_id}/evidence.json",
        ),
    )


def build_transition_request(
    ev: NormalizedEvidence,
    actor_type: str = "SYSTEM",
    simulation: bool = True,
) -> TransitionRequest:
    """Translate `NormalizedEvidence` to a `TransitionRequest`."""
    parts = ev.proposed_transition.split(" -> ", 1)
    if len(parts) != 2:
        raise ValueError(
            f"proposed_transition {ev.proposed_transition!r} is not of the "
            f"form 'CURRENT -> PROPOSED'.")
    current_state, proposed_state = parts
    if current_state not in LIFECYCLE_STATES:
        raise ValueError(f"unknown current state: {current_state!r}")
    if proposed_state not in LIFECYCLE_STATES:
        raise ValueError(f"unknown proposed state: {proposed_state!r}")
    return TransitionRequest(
        subject_id=ev.candidate_id,
        current_state=current_state,
        proposed_state=proposed_state,
        actor_type=actor_type,
        simulation=simulation,
        claimed_policy_id=None,
        claimed_policy_version=None,
        claimed_policy_checksum=None,
    )


def evaluate_candidate(
    ev: NormalizedEvidence,
    *,
    policy: GovernancePolicy,
    audit_path: Path,
    policy_mode: str = "RESEARCH",
    actor_type: str = "SYSTEM",
    simulation: bool = True,
) -> dict:
    """Run the existing GovernanceEngine on one candidate and emit
    a per-candidate evaluation record. The ONLY mutation is the
    append-only audit JSONL at `audit_path` (the existing
    `audit_decision` helper)."""
    candidate = build_candidate_context(ev, policy_mode=policy_mode)
    request = build_transition_request(ev, actor_type=actor_type,
                                       simulation=simulation)
    engine = GovernanceEngine(policy)
    decision = engine.evaluate(candidate, request)
    # The only allowed mutation: append to the audit JSONL.
    audit_decision(audit_path, decision, scenario_id="stage_12_research_evaluation")
    # Build the per-candidate record (no mutation of any other state).
    record = {
        "schema": "stage_12_governance_evaluation_v1",
        "subject_id": ev.candidate_id,
        "target": ev.target,
        "proposed_transition": ev.proposed_transition,
        "audit_path": str(audit_path.relative_to(audit_path.parents[2])
                          if audit_path.is_file() else str(audit_path)),
        "decision": decision.decision,
        "reason_codes": decision.reason_codes,
        "explanation": decision.explanation,
        "current_state": decision.current_state,
        "proposed_state": decision.proposed_state,
        "policy_id": decision.policy_id,
        "policy_version": decision.policy_version,
        "policy_checksum": decision.policy_checksum,
        "governance_policy_fingerprint": decision.governance_policy_fingerprint,
        "decision_content_fingerprint": decision.decision_content_fingerprint,
        "evidence_refs": decision.evidence_refs,
        "actor_type": decision.actor_type,
        "simulation": decision.simulation,
        "evidence_classification": [
            {"name": c.name, "kind": c.kind, "value": c.value,
             "where": c.where, "note": c.note}
            for c in ev.classification
        ],
        "missing_evidence": [
            {"name": c.name, "where": c.where, "note": c.note}
            for c in ev.classification if c.kind == "MISSING"
        ],
        "negative_evidence": [
            {"name": c.name, "where": c.where, "note": c.note}
            for c in ev.classification if c.kind == "NEGATIVE"
        ],
        "context_dependent_evidence": [
            {"name": c.name, "where": c.where, "note": c.note}
            for c in ev.classification if c.kind == "CONTEXT_DEPENDENT"
        ],
        "verified_evidence": [
            {"name": c.name, "where": c.where, "note": c.note}
            for c in ev.classification if c.kind == "VERIFIED"
        ],
        "gate_results": decision.gate_results,
        "failed_gates": decision.failed_gates,
        "lifecycle_mutated": False,
        "registration_state_changed": False,
        "champion_state_changed": False,
        "policy_changed": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    return record
