"""GET /health: API + research pipeline + productization health."""
from __future__ import annotations
import csv
import hashlib
import json
from pathlib import Path

from fastapi import APIRouter, Depends

from ..config import CONFIG
from ..dependencies import AppState, get_state
from ..schemas import HealthStatus

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthStatus,
            summary="API + research pipeline + productization health")
def health(state: AppState = Depends(get_state)) -> HealthStatus:
    """Honest health: the system is offline evaluation; no live monitoring."""
    artifacts = {}
    notes: list[str] = []
    root = state.project_root

    # The three CSVs are the only research artifacts needed for the API to function.
    required = [
        "artifacts/research_tables/final_forecasting_results.csv",
        "artifacts/research_tables/final_model_comparison.csv",
        "artifacts/research_tables/final_predictions.csv",
    ]
    for rel in required:
        path = root / rel
        artifacts[rel] = {"exists": path.exists(),
                          "size": path.stat().st_size if path.exists() else 0,
                          "sha256": hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None}

    # Optional: audit ledger and MLflow — not required to answer API queries.
    optional = [
        "artifacts/mlops/audit/events.jsonl",
        "config/governance/phase_13_policy.yaml",
        "artifacts/experimental_design/phase_19_final_evaluation_protocol_freeze.yaml",
    ]
    for rel in optional:
        path = root / rel
        artifacts[rel] = {"exists": path.exists(),
                          "size": path.stat().st_size if path.exists() else 0}

    required_ok = all(artifacts[rel]["exists"] for rel in required)
    research_pipeline = "READY" if required_ok else "DEGRADED"
    productization = "READY" if state.records and state.signals else "DEGRADED"
    api_status = "ok" if required_ok and state.records and state.signals else "degraded"
    if api_status != "ok":
        notes.append("One or more required research artefacts are missing; the API will return 503.")
    notes.append("This is an offline evaluation system. There is no live monitoring, no streaming, "
                 "no real-time telemetry, and no production deployment.")

    return HealthStatus(
        status=api_status,
        api="UP",
        research_pipeline=research_pipeline,
        productization=productization,
        artifacts=artifacts,
        notes=notes,
    )
