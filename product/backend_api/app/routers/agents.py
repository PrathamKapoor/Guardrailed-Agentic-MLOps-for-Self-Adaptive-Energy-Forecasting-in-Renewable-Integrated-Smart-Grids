"""POST /api/agents/explain: bounded agent explanations (advisory only).

The endpoint wraps the existing bounded agent layer (smartgrid_mlops.agents)
through the existing Orchestrator. It is read-only / advisory-only:

* No lifecycle action is exposed.
* The agent's recommendation passes the existing governance firewall
  (agents/firewall.py) before being returned.
* A blocked recommendation is returned as a 200 with firewall_decision =
  "blocked", not as an HTTP error, so the advisory behaviour is preserved.
* The endpoint never executes, deploys, retrains, or mutates anything.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..config import CONFIG
from ..dependencies import AppState, get_state
from ..schemas import AgentExplanationRequest, AgentExplanationResponse

router = APIRouter(prefix="/api/agents", tags=["agents"])


def _orchestrator(state: AppState):
    """Lazy-load the bounded agent Orchestrator from the existing implementation.

    The orchestrator uses the real agent pipeline (drift, performance,
    security, governance, redteam) and the existing governance firewall.
    """
    if "_orchestrator" not in state._orchestrator_handle:
        from smartgrid_mlops.agents.orchestrator import Orchestrator
        # The orchestrator requires a project_root. Use the canonical one.
        orch = Orchestrator(state.project_root,
                            audit_path=state.project_root / "artifacts/mlops/audit/events.jsonl",
                            memory_dir=state.project_root / "artifacts/agents/phase_18/memory")
        state._orchestrator_handle["_orchestrator"] = orch
    return state._orchestrator_handle["_orchestrator"]


@router.post("/explain", response_model=AgentExplanationResponse,
             summary="Bounded-agent explanation (advisory only; firewall-validated)")
def explain(req: AgentExplanationRequest,
            state: AppState = Depends(get_state)) -> AgentExplanationResponse:
    """The endpoint accepts a structured context and returns an advisory explanation.

    The request **must** be a bounded query. Lifecycle action types are
    not accepted as the query subject; they are intercepted by the firewall
    regardless of how the request is structured.
    """
    from smartgrid_mlops.agents.firewall import firewall_validate
    from smartgrid_mlops.agents.schemas import AgentQuery

    # The query is what the user wants explained. The bounded agent has a
    # fixed set of query types; map the user-supplied query string onto
    # EXPLAIN_DRIFT (or fallback) since this endpoint is the explanation
    # service. We do not interpret the free-form query string as a
    # command — it is recorded as the subject_id for audit only.
    query_type = "EXPLAIN_DRIFT"
    payload = {
        "drift_event": {
            "severity": "CRITICAL" if req.context.get("severity") in ("HIGH", "CRITICAL") else "NONE",
            "target": req.context.get("target", "unknown"),
            "scenario_id": "api-explainer",
            "triggered": req.context.get("detectors", ["UNKNOWN"]),
            "signal_values": req.context.get("signal_values", {}),
            "model": req.context.get("model", "unknown"),
        },
        "evidence_refs": req.context.get("evidence_refs", []),
    }
    agent_query = AgentQuery(query_type=query_type, payload=payload)

    orch = _orchestrator(state)
    result = orch.handle(agent_query)
    output = result["output"]
    firewall = result["firewall"]

    return AgentExplanationResponse(
        agent_id=output["agent_id"], agent_version=output["agent_version"],
        query_id=output["query_id"],
        input_evidence_refs=output["input_evidence_refs"],
        reasoning_summary=output["reasoning_summary"],
        recommendation=output["recommendation"],
        confidence=output["confidence"],
        limitations=output["limitations"],
        requires_human_review=output["requires_human_review"],
        timestamp=output["timestamp"],
        firewall_decision="allowed" if firewall["allowed"] else "blocked",
        firewall_reason_code=firewall["reason_code"],
    )


@router.get("/types", response_model=dict,
            summary="Bounded agent query types (advisory only; no lifecycle actions)")
def list_agent_types() -> dict:
    """List the bounded agent query types the API can dispatch.

    The set is fixed at the existing agent layer's QUERY_TYPES. Lifecycle
    actions are intentionally NOT in this list.
    """
    from smartgrid_mlops.agents.schemas import QUERY_TYPES, ALLOWED_RECOMMENDATIONS
    return {
        "query_types": sorted(QUERY_TYPES),
        "allowed_recommendation_types": sorted(ALLOWED_RECOMMENDATIONS),
        "notes": "Lifecycle action types are NOT exposed. The endpoint is advisory only.",
    }
