"""Phase 18 guards: no model changes, no final-test access, freeze integrity."""
from __future__ import annotations
import hashlib
from pathlib import Path

FINAL_TEST_FORBIDDEN = ("final_test", "final-test", "november", "december")

# Artifacts that must remain byte-identical across the ablation (no model changes).
PROTECTED_FREEZES = [
    "config/governance/phase_13_policy.yaml",
    "config/governance/phase_16_promotion_policy.yaml",
    "config/retraining/phase_15_policy.yaml",
    "config/monitoring/phase_14_drift.yaml",
    "artifacts/model_registry/lifecycle_registry.yaml",
    "artifacts/model_registry/phase_15_challengers.yaml",
    "artifacts/model_registry/phase_16_champion_registry.yaml",
]


def assert_no_final_test_access(value=None) -> None:
    if value and any(x in str(value).lower() for x in FINAL_TEST_FORBIDDEN):
        raise ValueError("PHASE18_FINAL_TEST_ACCESS_BLOCKED")


def snapshot_protected(project_root: Path) -> dict[str, str]:
    return {p: hashlib.sha256((Path(project_root) / p).read_bytes()).hexdigest() for p in PROTECTED_FREEZES}


def assert_no_model_changes(project_root: Path, baseline: dict[str, str] | None = None) -> None:
    if baseline is None: return
    current = snapshot_protected(project_root)
    for path, checksum in baseline.items():
        if current.get(path) != checksum:
            raise ValueError(f"MODEL_CHANGE_DETECTED: {path} changed during the ablation")
