"""Stage 13: governance-compatible candidate packaging.

This package builds formal, reproducible evidence packages for the
seven Stage 10 / Stage 11 research candidates and writes them under
`artifacts/v2/governance_candidate_packages/<candidate_id>/`. The
packages reuse the EXISTING fingerprint helpers in
`smartgrid_mlops.mlops.fingerprints` and the EXISTING finalist
registry in `artifacts/model_registry/mlops_research_registry.yaml`.

The Stage 13 layer is a PACKAGING and BENCHMARK-RECONCILIATION
layer only. It does NOT modify the frozen Phase 13 policy, the
governance engine, the agent firewall, the registry, the OpenAPI
surface, or any protected v1 artefact. It does NOT promote a model
or deploy a model. The only allowed mutation is writing the
candidate package files under `artifacts/v2/governance_candidate_packages/`.
"""
from .fingerprints import (
    ROOT, V2_ROOT, PHASE_19_PROTOCOL_FREEZE, PHASE_10_FEATURE_CONFIG,
    PHASE_13_POLICY_PATH, RESEARCH_INDEX, FINALIST_REGISTRY,
    FINAL_TEST_RESULTS, STAGE_10_EVIDENCE_DIR, STAGE_10_DEFAULT_TR,
    PHASE_10_FEATURES, RESIDUAL_FEATURE_NAMES, RESIDUAL_FEATURE_SET_ID,
    RESIDUAL_LAG_DESCRIPTIONS, CANDIDATE_MODEL_SPECS,
    model_spec_for, feature_spec_for,
    _strongest_development_benchmark, benchmark_evaluation_for,
    protocol_compatibility_for, _load_stage_10_metrics,
    write_candidate_package, run_all_packages,
)

__all__ = [
    "CANDIDATE_MODEL_SPECS",
    "FINAL_TEST_RESULTS",
    "FINALIST_REGISTRY",
    "PHASE_10_FEATURE_CONFIG",
    "PHASE_10_FEATURES",
    "PHASE_13_POLICY_PATH",
    "PHASE_19_PROTOCOL_FREEZE",
    "RESEARCH_INDEX",
    "RESIDUAL_FEATURE_NAMES",
    "RESIDUAL_FEATURE_SET_ID",
    "RESIDUAL_LAG_DESCRIPTIONS",
    "ROOT",
    "STAGE_10_DEFAULT_TR",
    "STAGE_10_EVIDENCE_DIR",
    "V2_ROOT",
    "_load_stage_10_metrics",
    "_strongest_development_benchmark",
    "benchmark_evaluation_for",
    "feature_spec_for",
    "model_spec_for",
    "protocol_compatibility_for",
    "run_all_packages",
    "write_candidate_package",
]
