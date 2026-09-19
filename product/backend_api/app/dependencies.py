"""App-state singletons for the API.

Loads Stage 1 productization records + monitoring signals + champion
snapshot ONCE at app startup. Routers read these via FastAPI dependencies.
The state is read-only; the API does not mutate it."""
from __future__ import annotations
import hashlib
import json
import logging
import sys
from dataclasses import dataclass
from pathlib import Path

from .config import CONFIG

logger = logging.getLogger("smartgrid_mlops.api.deps")

# Required for the API to answer. The list mirrors the contract enforced by
# the /health endpoint; if any of these is missing, the API cannot answer
# forecasts / models / monitoring / governance / audit queries.
REQUIRED_ARTIFACTS = (
    "artifacts/research_tables/final_forecasting_results.csv",
    "artifacts/research_tables/final_model_comparison.csv",
    "artifacts/research_tables/final_predictions.csv",
    "config/governance/phase_13_policy.yaml",
)

# Optional artefacts. Missing these is logged but does not abort startup.
OPTIONAL_ARTIFACTS = (
    "artifacts/mlops/audit/events.jsonl",
    "artifacts/experimental_design/phase_19_final_evaluation_protocol_freeze.yaml",
)


@dataclass(frozen=True)
class AppState:
    project_root: Path
    records: list               # list[ForecastingModelRecord]
    signals: list               # list[MonitoringEvent dicts]
    snapshot: dict              # ChampionRegistry snapshot dict
    metadata: dict              # Provenance metadata (sources, fingerprints, counts)
    _orchestrator_handle: dict  # Lazy orchestrator fixture (used by /agents/explain)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _validate_required_artifacts(project_root: Path) -> None:
    """Verify that every required artefact exists and is readable. The API
    is a read-only consumer of frozen Phase 19 evidence; if those files are
    absent, almost every endpoint will return a 500 — better to fail fast
    at startup with a clear message."""
    missing: list[str] = []
    for rel in REQUIRED_ARTIFACTS:
        path = project_root / rel
        if not path.is_file():
            missing.append(rel)
    if missing:
        joined = "\n  - ".join(missing)
        raise RuntimeError(
            "Required research artefacts are missing or unreadable under "
            f"project root {project_root}:\n  - {joined}\n"
            "Re-run the project bootstrap or set SMARTGRID_MLOPS_PROJECT_ROOT to a "
            "checkout that contains the frozen Phase 19 evidence."
        )
    for rel in OPTIONAL_ARTIFACTS:
        path = project_root / rel
        if not path.is_file():
            logger.info("optional artefact not present (non-fatal): %s", rel)


def _load_state() -> AppState:
    """Resolve the productization state once. Read-only with respect to
    all Phase 19 artefacts."""
    project_root = CONFIG.project_root
    _validate_required_artifacts(project_root)
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root / "src"))
    from smartgrid_mlops.productization import (
        build_forecasting_records,
        build_monitoring_signals,
        build_champion_challenger_snapshot,
    )
    records = build_forecasting_records(project_root)
    signals = build_monitoring_signals(records, project_root)
    snapshot = build_champion_challenger_snapshot(records, project_root)
    metadata = {
        "records_count": len(records),
        "signals_count": len(signals),
        "snapshot_targets": list(snapshot.get("champions", {}).keys()),
        "project_root_sha": _sha256(project_root / "pyproject.toml"),
        "phase_19_protocol_freeze_sha": _sha256(
            project_root / "artifacts/experimental_design/phase_19_final_evaluation_protocol_freeze.yaml"),
        "phase_13_policy_sha": _sha256(
            project_root / "config/governance/phase_13_policy.yaml"),
    }
    return AppState(project_root=project_root, records=records, signals=signals,
                    snapshot=snapshot, metadata=metadata, _orchestrator_handle={})


STATE = _load_state()


def get_state() -> AppState:
    return STATE
