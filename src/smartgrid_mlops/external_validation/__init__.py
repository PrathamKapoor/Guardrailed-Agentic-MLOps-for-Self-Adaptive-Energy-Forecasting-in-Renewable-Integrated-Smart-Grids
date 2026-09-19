"""External validation package — evaluation-only assessment on approved independent datasets.

This package is evaluation-only: frozen configurations from Phase 19 are applied
to external data without retuning. No model selection may be derived from
external results.
"""
from __future__ import annotations

from .spec import ExternalValidationSpec, dataset_requirements
from .validation import (
    DatasetNotAvailableError,
    FeatureCompatibilityError,
    ProvenanceError,
    validate_dataset_manifest,
    validate_feature_compatibility,
    validate_temporal_coverage,
)

__all__ = [
    "DatasetNotAvailableError",
    "ExternalValidationSpec",
    "FeatureCompatibilityError",
    "ProvenanceError",
    "dataset_requirements",
    "validate_dataset_manifest",
    "validate_feature_compatibility",
    "validate_temporal_coverage",
]
