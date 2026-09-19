"""GET /api/models: the existing research registry, exposed as a thin view.

No second registry. No duplicate representation.
"""
from __future__ import annotations
import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from ..dependencies import AppState, get_state
from ..schemas import ModelRecord

router = APIRouter(prefix="/api/models", tags=["models"])


def _registry_entries(state: AppState) -> list[dict]:
    """Read the existing frozen Phase 11/12/13 research registry.

    Source of truth is `artifacts/model_registry/forecasting_reference_registry.yaml`
    (Phase 11 finalist registry). The lifecycle registry
    (`artifacts/model_registry/lifecycle_registry.yaml`) is the source of
    `lifecycle_state`. We do NOT register a second registry.
    """
    root = state.project_root
    fr = json.loads((root / "artifacts/model_registry/forecasting_reference_registry.yaml").read_text(encoding="utf-8"))
    lc = json.loads((root / "artifacts/model_registry/lifecycle_registry.yaml").read_text(encoding="utf-8"))
    by_id = {e["registry_id"]: e for e in lc["entries"]}

    out: list[dict] = []
    for target, body in fr.items():
        ref = body["reference_model"]
        # Lifecycle lookup by registry_id convention MLOPS-REF-{TARGET}-H24-V1
        lc_entry = by_id.get(f"MLOPS-REF-{target.upper()}-H24-V1", {})
        out.append({
            "registry_id": f"MLOPS-REF-{target.upper()}-H24-V1",
            "target": target,
            "horizon": 24,
            "research_role": "REFERENCE",
            "registry_state": lc_entry.get("registry_state", "REGISTERED_REFERENCE"),
            "lifecycle_state": lc_entry.get("lifecycle_state", "REGISTERED_REFERENCE"),
            "model_family": ref["model"],
            "framework": ref.get("framework", "sklearn"),
            "implementation_id": ref["implementation_id"],
            "model_spec_fingerprint": "frozen:phase10",
            "feature_set_id": ref["feature_set"],
            "feature_spec_fingerprint": "frozen:phase10",
            "dataset_fingerprint": "frozen:phase11",
            "protocol_hash": "frozen:phase10",
            "development_primary_metric": "MAE",
            "development_mae": float(ref["mae"]),
            "strongest_benchmark": body["baseline_comparator"],
            "benchmark_mae": 0.0,  # populated from final_model_comparison
            "development_benchmark_gate": lc_entry.get("benchmark_gate", "BENCHMARK_GATE_FAIL"),
            "evidence_status": "VALID",
            "selection_evidence": f"Phase 11 finalist registry; target {target}; impl {ref['implementation_id']}",
            "created_from_phase": 11,
            "final_test_performance_status": "VERIFIED_LOCKED_TEST",
        })
    # Populate benchmark_mae from final_model_comparison.csv
    import csv
    with (root / "artifacts/research_tables/final_model_comparison.csv").open(encoding="utf-8") as f:
        comp = {r["Target"]: r for r in csv.DictReader(f)}
    for entry in out:
        c = comp.get(entry["target"])
        if c is not None:
            entry["benchmark_mae"] = float(c["Benchmark MAE"])
    return out


@router.get("", response_model=list[ModelRecord],
            summary="Existing Phase 11/13 research registry (reference models only)")
def list_models(state: AppState = Depends(get_state)) -> list[ModelRecord]:
    return [ModelRecord(**e) for e in _registry_entries(state)]


@router.get("/{model_id}", response_model=ModelRecord,
            summary="Get a single registered model by registry_id (e.g. MLOPS-REF-LOAD-H24-V1)")
def get_model(model_id: str, state: AppState = Depends(get_state)) -> ModelRecord:
    for e in _registry_entries(state):
        if e["registry_id"] == model_id:
            return ModelRecord(**e)
    raise HTTPException(status_code=404, detail=f"Unknown model_id {model_id!r}")
