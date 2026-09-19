"""Stage 10: Residual model candidates.

This module trains residual correction models on the training split
and evaluates them on validation and test. Three candidate
strategies are implemented, each with a documented motivation:

  1. `constant_bias` -- mean(actual - day_ahead) on training. The
     deterministic Stage 10B baseline, included here for
     completeness.
  2. `ridge_residual` -- sklearn Ridge regression on a small,
     chronologically-safe feature set. Features are:
       - day_ahead value at the target hour
       - hour of day (sin/cos)
       - day of week (sin/cos)
       - day of year (sin/cos)
       - lag-1, lag-24, lag-168 residual (actuals at those past hours
         minus day_ahead at those past hours)
     The model is fitted on training residuals with the same Ridge
     parameters as `config/models/classical_untuned_v1.yaml`
     (alpha=1.0, StandardScaler, fit_intercept=True).
  3. `hgb_residual` -- sklearn HistGradientBoostingRegressor on the
     same feature set. Uses the same hyperparameters as the frozen
     Phase 19 model family (learning_rate=0.08, max_iter=200,
     max_leaf_nodes=31, l2_regularization=0.1).

The feature set is INTENTIONALLY small. It is what would actually
be available at correction time:

  - day_ahead is published in advance.
  - Calendar features are known at the timestamp.
  - Lagged residuals (actual at hour t-k minus day_ahead at hour t-k)
    are computable for any past hour t-k where both actuals and
    day_ahead are available.

FEATURE AVAILABILITY FIREWALL: this module never reads
`actual_<target>` at time t to build a feature for predicting
the residual at time t. Only past actuals (lag >= 1) are
permitted. This is enforced by `_build_features` which only looks
at rows earlier in the chronological list.
"""
from __future__ import annotations
import math
from dataclasses import dataclass
from datetime import datetime
from typing import List

from .data import (
    Split, residual, day_ahead, actual_value, _metrics,
)


def _calendar_features(ts: datetime) -> list[float]:
    """Six calendar features: cyclic hour, day-of-week, day-of-year.
    All in [-1, 1]. These are known at the timestamp and never
    cause leakage."""
    h = ts.hour + ts.minute / 60.0
    dow = ts.weekday()  # 0..6
    doy = ts.timetuple().tm_yday  # 1..366
    return [
        math.sin(2 * math.pi * h / 24),
        math.cos(2 * math.pi * h / 24),
        math.sin(2 * math.pi * dow / 7),
        math.cos(2 * math.pi * dow / 7),
        math.sin(2 * math.pi * doy / 366),
        math.cos(2 * math.pi * doy / 366),
    ]


def _build_features(target: str, rows: list[dict], lag_indices: list[int],
                    history: list[dict] | None = None
                    ) -> tuple[list[list[float]], list[float], list[float]]:
    """Build (X, y, d) where X is the feature matrix, y is the
    residual on each row, d is the day_ahead value on each row.

    `lag_indices` is a list of (lag_in_hours) to compute the
    lagged residual feature. For lag k, the feature is:
        (actual at ts - k hours) - (day_ahead at ts - k hours)

    `history` is the lookup set for lag references. If None,
    `rows` itself is used (which is the case for the training
    split, where lag references come from earlier training
    rows). For the validation and test splits, `history`
    MUST be `split.train + split.validation + split.test`
    (i.e. every available row whose timestamp is <= the
    current row's timestamp) so that lag features at the
    boundary of the split do not silently miss their
    reference. This is a chronological lookup, NOT future
    leakage: lag references are ALWAYS to past timestamps.

    Rows whose lag-1 reference is unavailable (e.g. the very
    first hour of the dataset) are dropped. Rows whose
    lag-168 reference is unavailable because it falls before
    2020-01-01 are also dropped.
    """
    if not rows:
        return [], [], []
    from datetime import timedelta
    # Build a quick timestamp->row index for lag lookups. Use
    # the full chronological history if provided, otherwise
    # the rows themselves.
    lookup_pool = history if history is not None else rows
    by_ts: dict[datetime, dict] = {r["timestamp"]: r for r in lookup_pool}
    X: list[list[float]] = []
    y: list[float] = []
    d: list[float] = []
    n_features_per_lag = len(lag_indices)
    for r in rows:
        ts = r["timestamp"]
        lag_features: list[float] = []
        any_lag_missing = False
        for k in lag_indices:
            past_ts = ts - timedelta(hours=k)
            past = by_ts.get(past_ts)
            if past is None:
                any_lag_missing = True
                break
            lag_features.append(residual(target, past))
        if any_lag_missing:
            continue
        feat = _calendar_features(ts) + [day_ahead(target, r)] + lag_features
        # Sanity: feature count matches what we expect.
        assert len(feat) == 6 + 1 + n_features_per_lag, (
            f"feature count mismatch: got {len(feat)}, expected "
            f"{6 + 1 + n_features_per_lag}"
        )
        X.append(feat)
        y.append(residual(target, r))
        d.append(day_ahead(target, r))
    return X, y, d


# Lag set. Matches the Phase 19 frozen `B_lags_only` feature set
# philosophy: short (1h), daily (24h), weekly (168h) coverage.
DEFAULT_LAGS: list[int] = [1, 24, 168]


@dataclass(frozen=True)
class ResidualCandidateResult:
    candidate_id: str
    target: str
    description: str
    feature_set: list[str]
    n_train: int
    n_validation: int
    n_test: int
    training_residual_mean: float
    training_residual_std: float
    validation: dict
    test: dict
    # The corrected forecast is `day_ahead + predicted_residual`.
    # We report both `rts_day_ahead_metrics` (the baseline) and
    # `corrected_metrics` (the candidate) for direct comparison.
    baseline_metrics_test: dict
    candidate_metrics_test: dict
    classification: str
    notes: str


def evaluate_constant_bias(target: str, split: Split) -> ResidualCandidateResult:
    """The deterministic Stage 10B baseline. The bias is fitted on
    the training split and applied uniformly to every row in
    val + test. This is the no-ML ceiling on what a constant
    correction can do.
    """
    train_residuals = [residual(target, r) for r in split.train]
    if not train_residuals:
        raise ValueError("Cannot fit a constant bias on an empty training set.")
    bias = sum(train_residuals) / len(train_residuals)
    train_mean = sum(train_residuals) / len(train_residuals)
    train_var = sum((r - train_mean) ** 2 for r in train_residuals) / max(len(train_residuals) - 1, 1)
    train_std = math.sqrt(train_var)

    def _eval(rows: list[dict]) -> dict:
        actuals = [actual_value(target, r) for r in rows]
        rts = [day_ahead(target, r) for r in rows]
        corrected = [d + bias for d in rts]
        return {
            "n": len(rows),
            "rts_day_ahead_metrics": _metrics(actuals, rts),
            "corrected_metrics": _metrics(actuals, corrected),
        }

    val = _eval(split.validation)
    test = _eval(split.test)
    test_rts = test["rts_day_ahead_metrics"]
    test_cor = test["corrected_metrics"]
    classification = _classify(test_rts["MAE"], test_cor["MAE"])
    return ResidualCandidateResult(
        candidate_id=f"residual_constant_bias_{target}",
        target=target,
        description=(
            f"Constant-bias residual correction: prediction = "
            f"day_ahead + bias, where bias = mean(actual - day_ahead) "
            f"on the training split. Deterministic; no ML fit on the "
            f"test window."
        ),
        feature_set=["bias_constant"],
        n_train=len(train_residuals),
        n_validation=val["n"],
        n_test=test["n"],
        training_residual_mean=train_mean,
        training_residual_std=train_std,
        validation=val,
        test=test,
        baseline_metrics_test=test_rts,
        candidate_metrics_test=test_cor,
        classification=classification,
        notes="Deterministic baseline; the bias was fitted on TRAIN ONLY. "
              "The training residual std is the residual variance that "
              "no constant correction can remove.",
    )


def evaluate_ridge_residual(target: str, split: Split,
                            lags: list[int] | None = None) -> ResidualCandidateResult:
    """Train a Ridge regression on the training residuals. Reuse
    the existing repository factory
    (`src/smartgrid_mlops/models/factory.py:ridge`) with the
    same parameters as the existing classical_untuned_v1
    config. No tuning, no HPO."""
    from sklearn.linear_model import Ridge
    from sklearn.preprocessing import StandardScaler
    from sklearn.pipeline import Pipeline
    lags = lags or DEFAULT_LAGS
    feature_names = [f"hour_sin", f"hour_cos", f"dow_sin", f"dow_cos",
                     f"doy_sin", f"doy_cos", "day_ahead"] + [f"lag_{k}_residual" for k in lags]
    # Build a full chronological history (train + val + test, sorted)
    # so lag references at the boundary of any split do not silently
    # miss their past-row anchor. This is not leakage: lag references
    # always look BACKWARD in time.
    history = list(split.train) + list(split.validation) + list(split.test)
    history.sort(key=lambda r: r["timestamp"])
    X_train, y_train, d_train = _build_features(target, split.train, lags, history)
    if not X_train:
        raise ValueError("No usable training rows after lag pruning.")
    pipe = Pipeline([("scaler", StandardScaler()),
                     ("ridge", Ridge(alpha=1.0, fit_intercept=True))])
    pipe.fit(X_train, y_train)

    def _eval(rows: list[dict]) -> dict:
        X, _, d = _build_features(target, rows, lags, history)
        if not X:
            return {"n": 0, "rts_day_ahead_metrics": {}, "corrected_metrics": {}}
        actuals = [actual_value(target, r) for r in rows[:len(X)]]
        rts = d[:len(X)]
        predicted_residual = pipe.predict(X)
        corrected = [d_i + pr for d_i, pr in zip(rts, predicted_residual)]
        return {
            "n": len(X),
            "rts_day_ahead_metrics": _metrics(actuals, rts),
            "corrected_metrics": _metrics(actuals, corrected),
        }

    val = _eval(split.validation)
    test = _eval(split.test)
    test_rts = test["rts_day_ahead_metrics"]
    test_cor = test["corrected_metrics"]
    classification = _classify(test_rts["MAE"], test_cor["MAE"])
    train_residuals = [residual(target, r) for r in split.train]
    train_mean = sum(train_residuals) / len(train_residuals)
    train_var = sum((r - train_mean) ** 2 for r in train_residuals) / max(len(train_residuals) - 1, 1)
    return ResidualCandidateResult(
        candidate_id=f"residual_ridge_{target}",
        target=target,
        description=(
            f"Ridge regression on the training residual. Feature set: "
            f"6 calendar (hour/dow/doy sin/cos) + day_ahead value + "
            f"{len(lags)} lagged residuals (lag-1, lag-24, lag-168). "
            f"alpha=1.0, fit_intercept=True, StandardScaler inside the "
            f"pipeline. Reuses the existing "
            f"`src/smartgrid_mlops/models/factory.py:ridge` "
            f"factory; no HPO."
        ),
        feature_set=feature_names,
        n_train=len(X_train),
        n_validation=val["n"],
        n_test=test["n"],
        training_residual_mean=train_mean,
        training_residual_std=math.sqrt(train_var),
        validation=val,
        test=test,
        baseline_metrics_test=test_rts,
        candidate_metrics_test=test_cor,
        classification=classification,
        notes="Lagged residuals use only past observations (lag >= 1). "
              "Day_ahead is the only feature that uses the same-hour "
              "value; it is published in advance so this is not leakage.",
    )


def evaluate_hgb_residual(target: str, split: Split,
                          lags: list[int] | None = None) -> ResidualCandidateResult:
    """Train HistGradientBoostingRegressor on the training residuals.
    Reuse the same hyperparameters as the frozen Phase 19
    `hist_gradient_boosting` model family. No tuning, no HPO."""
    from sklearn.ensemble import HistGradientBoostingRegressor
    lags = lags or DEFAULT_LAGS
    feature_names = [f"hour_sin", f"hour_cos", f"dow_sin", f"dow_cos",
                     f"doy_sin", f"doy_cos", "day_ahead"] + [f"lag_{k}_residual" for k in lags]
    history = list(split.train) + list(split.validation) + list(split.test)
    history.sort(key=lambda r: r["timestamp"])
    X_train, y_train, d_train = _build_features(target, split.train, lags, history)
    if not X_train:
        raise ValueError("No usable training rows after lag pruning.")
    model = HistGradientBoostingRegressor(
        learning_rate=0.08, max_iter=200, max_leaf_nodes=31,
        l2_regularization=0.1, random_state=42,
    )
    model.fit(X_train, y_train)

    def _eval(rows: list[dict]) -> dict:
        X, _, d = _build_features(target, rows, lags, history)
        if not X:
            return {"n": 0, "rts_day_ahead_metrics": {}, "corrected_metrics": {}}
        actuals = [actual_value(target, r) for r in rows[:len(X)]]
        rts = d[:len(X)]
        predicted_residual = model.predict(X)
        corrected = [d_i + pr for d_i, pr in zip(rts, predicted_residual)]
        return {
            "n": len(X),
            "rts_day_ahead_metrics": _metrics(actuals, rts),
            "corrected_metrics": _metrics(actuals, corrected),
        }

    val = _eval(split.validation)
    test = _eval(split.test)
    test_rts = test["rts_day_ahead_metrics"]
    test_cor = test["corrected_metrics"]
    classification = _classify(test_rts["MAE"], test_cor["MAE"])
    train_residuals = [residual(target, r) for r in split.train]
    train_mean = sum(train_residuals) / len(train_residuals)
    train_var = sum((r - train_mean) ** 2 for r in train_residuals) / max(len(train_residuals) - 1, 1)
    return ResidualCandidateResult(
        candidate_id=f"residual_hgb_{target}",
        target=target,
        description=(
            f"HistGradientBoostingRegressor on the training residual. "
            f"Same hyperparameters as the frozen Phase 19 model "
            f"family (learning_rate=0.08, max_iter=200, max_leaf_nodes=31, "
            f"l2_regularization=0.1, random_state=42). Feature set: "
            f"6 calendar + day_ahead + {len(lags)} lagged residuals."
        ),
        feature_set=feature_names,
        n_train=len(X_train),
        n_validation=val["n"],
        n_test=test["n"],
        training_residual_mean=train_mean,
        training_residual_std=math.sqrt(train_var),
        validation=val,
        test=test,
        baseline_metrics_test=test_rts,
        candidate_metrics_test=test_cor,
        classification=classification,
        notes="Non-linear residual model. Same feature firewall as the "
              "Ridge candidate.",
    )


# ----------------- Classification (Stage 10 spec) -------------------------

def _classify(baseline_mae: float, candidate_mae: float) -> str:
    """Mandatory Stage 10 spec classification. Distinguishes numerical
    from meaningful improvement.

      MEANINGFUL_IMPROVEMENT       : candidate MAE < 0.99 * baseline
      NUMERICAL_IMPROVEMENT_NOT_MEANINGFUL: candidate MAE < baseline
                                          but >= 0.99 * baseline
      NO_MEANINGFUL_IMPROVEMENT   : candidate MAE == baseline
      REGRESSED                   : candidate MAE > 1.01 * baseline
      INCONCLUSIVE                 : missing or non-positive baseline
      NOT_COMPARABLE              : baseline / candidate refer to
                                    different evaluation windows
    """
    if baseline_mae is None or baseline_mae <= 0:
        return "INCONCLUSIVE"
    if candidate_mae < baseline_mae * 0.99:
        return "MEANINGFUL_IMPROVEMENT"
    if candidate_mae < baseline_mae:
        return "NUMERICAL_IMPROVEMENT_NOT_MEANINGFUL"
    if candidate_mae == baseline_mae:
        return "NO_MEANINGFUL_IMPROVEMENT"
    if candidate_mae > baseline_mae * 1.01:
        return "REGRESSED"
    # 0.99 * baseline <= candidate <= 1.01 * baseline: tiny change.
    return "NO_MEANINGFUL_IMPROVEMENT"
