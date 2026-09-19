"""Stage 11: Research validation of Stage 10 residual candidates."""
from .folds import (
    Fold, chronological_folds, LOCKED_TEST_START, LOCKED_TEST_END,
    SOURCE_PARQUET,
)
from .leakage import (
    FeatureAvailability, stage_10_feature_table, write_leakage_audit,
    plant_future_leak_check, run_leakage_audit,
)
from .runner import (
    FOLD_RESULTS_DIR, SEED_STABILITY_DIR, ABLATION_DIR, HGB_SEEDS,
    evaluate_fold, run_per_fold_evaluation, evaluate_hgb_seeds,
    run_seed_stability, _fold_to_split,
)
from .ablation import (
    ABLATION_SPECS, AblationSpec, run_ablations,
)
from .distribution import (
    DIST_DIR, FoldDistribution, fold_distribution, run_distribution_analysis,
)

__all__ = [
    "ABLATION_DIR",
    "ABLATION_SPECS",
    "DIST_DIR",
    "FOLD_RESULTS_DIR",
    "FeatureAvailability",
    "Fold",
    "FoldDistribution",
    "HGB_SEEDS",
    "LOCKED_TEST_END",
    "LOCKED_TEST_START",
    "SEED_STABILITY_DIR",
    "SOURCE_PARQUET",
    "AblationSpec",
    "_fold_to_split",
    "chronological_folds",
    "evaluate_fold",
    "evaluate_hgb_seeds",
    "fold_distribution",
    "plant_future_leak_check",
    "run_ablations",
    "run_distribution_analysis",
    "run_leakage_audit",
    "run_per_fold_evaluation",
    "run_seed_stability",
    "stage_10_feature_table",
    "write_leakage_audit",
]
