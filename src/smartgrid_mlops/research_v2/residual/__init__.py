"""Stage 10: Residual forecast correction research."""
from .data import (
    Split, TARGETS, TEST_START, TEST_END, TRAIN_END_EXCLUSIVE,
    VAL_END_EXCLUSIVE, chronological_split, residual, day_ahead,
    actual_value, residual_summary, constant_bias_baseline,
)
from .features import (
    DEFAULT_LAGS, ResidualCandidateResult, evaluate_constant_bias,
    evaluate_ridge_residual, evaluate_hgb_residual,
)
from .evidence import (
    V2_ROOT, EVIDENCE_DIR, run_target_research, run_all,
    _classify_no_research,
)

__all__ = [
    "DEFAULT_LAGS",
    "EVIDENCE_DIR",
    "ResidualCandidateResult",
    "Split",
    "TARGETS",
    "TEST_END",
    "TEST_START",
    "TRAIN_END_EXCLUSIVE",
    "VAL_END_EXCLUSIVE",
    "V2_ROOT",
    "_classify_no_research",
    "actual_value",
    "chronological_split",
    "constant_bias_baseline",
    "day_ahead",
    "evaluate_constant_bias",
    "evaluate_hgb_residual",
    "evaluate_ridge_residual",
    "residual",
    "residual_summary",
    "run_all",
    "run_target_research",
]
