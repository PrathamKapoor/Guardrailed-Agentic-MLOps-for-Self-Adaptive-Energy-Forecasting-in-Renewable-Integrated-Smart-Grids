# Baseline forecasting

## Baseline Selection Rationale

Phase 6 quantifies explicit historical rules before trainable models. All predictions use target timestamps eligible in the matching frozen Phase 5 feature matrix.

## H1 Persistence

For H1, persistence is \(\hat y(T)=y(T-1\,hour)\), obtained by explicit timestamp lookup and validated as available at origin.

## H1 Daily Seasonal Persistence

The H1 daily seasonal rule is \(\hat y(T)=y(T-24\,hours)\), with the same source-at-or-before-origin invariant.

## H1 Weekly Seasonal Persistence

The H1 weekly seasonal rule is \(\hat y(T)=y(T-168\,hours)\), using timestamp lookup rather than dataframe offsets.

## H24 Daily Persistence

H24 daily persistence is \(\hat y(T)=y(T-24\,hours)\). At this fixed horizon, origin persistence and target-minus-24-hour seasonal persistence are identical. They are recorded once as `H24_DAILY_PERSISTENCE` to avoid duplicate pseudo-results.

## H24 Weekly Seasonal Persistence

The H24 weekly rule is \(\hat y(T)=y(T-168\,hours)\), with an explicit availability validation.

## RTS-GMLC DAY_AHEAD Benchmark

Aligned RTS-GMLC `DAY_AHEAD` is an external H24 benchmark, never an independent ML feature. Exact issuance semantics are undocumented, so it is conceptually compared with H24 rather than represented as a proven fixed 24-hour lead forecast.

## Fair Timestamp Alignment

Each baseline uses only corresponding feature-matrix eligible timestamps and retains origin, target timestamp, fold identifier, actual, prediction, and error sequence. Final-test timestamps are rejected.

## Evaluation Metrics

MAE is primary. RMSE, zero-safe sMAPE, nMAE, and nRMSE reuse frozen Phase 5 definitions. PV nighttime zeros are retained.

## Validation Procedure

Results cover six May--October expanding folds and the September--October aggregate validation holdout. No final-test metric was accessed.

## Limitations

Fold variation is temporal, not stochastic, because baselines are deterministic. One-year coverage and uncertain DAY_AHEAD issuance semantics limit generalization.

## Final-Test Isolation

November--December remains locked for later explicitly authorized final evaluation.
