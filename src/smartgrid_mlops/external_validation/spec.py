"""External validation specification.

Defines dataset, feature, model, and evaluation requirements per
docs/research_methodology/external_validation.md. Pure data structures —
no I/O, no model training.
"""
from __future__ import annotations

from dataclasses import dataclass, field

MIN_EVALUABLE_SAMPLES = 720
MAX_MISSING_FRACTION_FOR_CONCLUSIVE = 0.10
REQUIRED_TARGETS = ("load", "wind", "pv")
PRIMARY_HORIZON = 24
PRIMARY_METRIC = "MAE"
SECONDARY_METRICS = ("RMSE", "sMAPE", "nMAE", "nRMSE")

# Feature sets from config/ablation/phase_10.yaml
FEATURE_SETS = {
    "B_lags_only": ["lag_1", "lag_24", "lag_168"],
    "E_full": [
        "hour_sin",
        "hour_cos",
        "dow_sin",
        "dow_cos",
        "doy_sin",
        "doy_cos",
        "lag_1",
        "lag_24",
        "lag_168",
        "rolling_mean_24",
        "rolling_mean_168",
        "ramp_1h",
    ],
}

# Frozen reference mapping as of Phase 19 (for documentation / enforcement)
FROZEN_REFERENCE = {
    "load": {"model": "random_forest", "feature_set": "B_lags_only"},
    "wind": {"model": "hist_gradient_boosting", "feature_set": "B_lags_only"},
    "pv": {"model": "random_forest", "feature_set": "B_lags_only"},
}


@dataclass(frozen=True)
class DatasetRequirements:
    min_samples_per_target: int = MIN_EVALUABLE_SAMPLES
    required_temporal_coverage_hours: int = MIN_EVALUABLE_SAMPLES
    sampling_frequency: str = "hourly"
    primary_horizon: int = PRIMARY_HORIZON
    missing_fraction_threshold: float = MAX_MISSING_FRACTION_FOR_CONCLUSIVE
    required_targets: tuple[str, ...] = REQUIRED_TARGETS


@dataclass(frozen=True)
class ModelPolicy:
    frozen_plan_path: str = "artifacts/experimental_design/final_test_comparison_plan.yaml"
    protocol_freeze_path: str = "artifacts/experimental_design/phase_10_ablation_protocol_freeze.yaml"
    hpo_best_config_pattern: str = "artifacts/experiments/hpo/phase_09/best_configs/{target}_pytorch_mlp.yaml"
    feature_config_path: str = "config/ablation/phase_10.yaml"
    allow_retuning: bool = False


@dataclass(frozen=True)
class EvaluationPolicy:
    primary_metric: str = PRIMARY_METRIC
    secondary_metrics: tuple[str, ...] = SECONDARY_METRICS
    statistical_test: str = "Diebold-Mariano (Newey-West lag 23) + Holm-Bonferroni alpha=0.05"
    aggregation: str = "all evaluable timestamps per target; fold-wise if multi-month"


@dataclass(frozen=True)
class GovernancePolicy:
    evaluation_only: bool = True
    promotion_allowed: bool = False
    agent_authority: str = "advisory only; deterministic policy gates authoritative"


@dataclass(frozen=True)
class ReproducibilityRequirements:
    manifest_required_fields: tuple[str, ...] = (
        "source",
        "license",
        "retrieval_date",
        "version",
        "schema",
        "approval",
        "archive_checksum",
    )
    artifact_structure: str = "artifacts/experiments/external_validation/<dataset>_<version>/"


@dataclass(frozen=True)
class ExternalValidationSpec:
    dataset: DatasetRequirements = field(default_factory=DatasetRequirements)
    model: ModelPolicy = field(default_factory=ModelPolicy)
    evaluation: EvaluationPolicy = field(default_factory=EvaluationPolicy)
    governance: GovernancePolicy = field(default_factory=GovernancePolicy)
    reproducibility: ReproducibilityRequirements = field(default_factory=ReproducibilityRequirements)


def dataset_requirements() -> DatasetRequirements:
    return DatasetRequirements()
