"""GET /api/governance: existing governance policy + decision evaluation.

The API evaluates transitions through the existing GovernanceEngine
with the frozen Phase 13 policy. It is read-only: it produces GovernanceDecision
records but does NOT persist lifecycle changes to the registries. That is
the existing research pipeline's job.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..dependencies import AppState, get_state
from ..schemas import GovernanceDecisionRecord, PolicyInfo

router = APIRouter(prefix="/api/governance", tags=["governance"])


def _load_policy(root: Path) -> PolicyInfo:
    policy_path = root / "config/governance/phase_13_policy.yaml"
    if not policy_path.exists():
        raise HTTPException(status_code=503, detail=f"Policy file missing: {policy_path}")
    text = policy_path.read_text(encoding="utf-8")
    doc = json.loads(text)  # file is JSON-formatted with .yaml extension
    from smartgrid_mlops.governance.policies import GovernancePolicy
    policy = GovernancePolicy.load(policy_path)
    # The frozen policy document does not include a top-level `lifecycle_states` or
    # `reason_codes` mapping; derive them from the existing governance schemas so the
    # API response is fully populated from the same source of truth.
    from smartgrid_mlops.governance.schemas import LIFECYCLE_STATES as _LCS
    from smartgrid_mlops.governance.decisions import EXPLANATIONS as _EXPL
    lifecycle_states = sorted(_LCS)
    reason_codes = sorted(_EXPL.keys())
    return PolicyInfo(
        policy_id=policy.policy_id, policy_version=policy.version,
        policy_checksum=policy.checksum,
        governance_policy_fingerprint=policy.governance_policy_fingerprint,
        lifecycle_states=lifecycle_states,
        reason_codes=reason_codes,
        source_path=str(policy_path.relative_to(root)),
    )


@router.get("/policy", response_model=PolicyInfo, summary="Frozen Phase 13 governance policy")
def get_policy(state: AppState = Depends(get_state)) -> PolicyInfo:
    return _load_policy(state.project_root)


class GovernanceEvaluateRequest(BaseModel):
    subject_id: str
    current_state: str
    proposed_state: str
    actor_type: str = "AGENT"
    simulation: bool = True
    claimed_policy_id: Optional[str] = None
    claimed_policy_version: Optional[str] = None
    claimed_policy_checksum: Optional[str] = None
    evidence_status: str = "VALID"
    benchmark_gate: str = "BENCHMARK_GATE_PASS"
    approval_state: str = "NOT_REQUIRED"


@router.post("/decisions", response_model=GovernanceDecisionRecord,
             summary="Evaluate a single transition through the existing GovernanceEngine (read-only, no mutation)")
def evaluate_decision(req: GovernanceEvaluateRequest,
                     state: AppState = Depends(get_state)) -> GovernanceDecisionRecord:
    from smartgrid_mlops.productization import build_governance_decision
    try:
        decision = build_governance_decision(
            state.project_root, subject_id=req.subject_id,
            current_state=req.current_state, proposed_state=req.proposed_state,
            actor_type=req.actor_type, simulation=req.simulation,
            claimed_policy_id=req.claimed_policy_id,
            claimed_policy_version=req.claimed_policy_version,
            claimed_policy_checksum=req.claimed_policy_checksum,
            evidence_status=req.evidence_status, benchmark_gate=req.benchmark_gate,
            approval_state=req.approval_state,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return GovernanceDecisionRecord(
        decision_id=decision.decision_id, subject_id=decision.subject_id,
        requested_transition=decision.requested_transition, decision=decision.decision,
        current_state=decision.current_state, proposed_state=decision.proposed_state,
        policy_id=decision.policy_id, policy_version=decision.policy_version,
        policy_checksum=decision.policy_checksum, reason_codes=decision.reason_codes,
        explanation=decision.explanation,
        decision_content_fingerprint=decision.decision_content_fingerprint,
        timestamp=decision.timestamp, gate_results=decision.gate_results,
        actor_type=decision.actor_type, simulation=decision.simulation,
    )


@router.get("/decisions", response_model=list[dict],
            summary="Existing governance decision log (from artifacts/governance/phase_13/decisions.jsonl)")
def list_decisions(limit: int = 100, state: AppState = Depends(get_state)) -> list[dict]:
    """Existing decision log from the Phase 13 evidence-ledger JSONL file."""
    path = state.project_root / "artifacts/governance/phase_13/decisions.jsonl"
    if not path.exists():
        return []
    out: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
        if len(out) >= limit:
            break
    return out
