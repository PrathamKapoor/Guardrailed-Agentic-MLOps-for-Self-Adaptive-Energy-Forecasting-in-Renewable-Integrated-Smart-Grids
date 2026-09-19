# Phase 06 completion report

## Phase status

**COMPLETE.** Phase 6 established deterministic, validation-only baseline forecasting evidence; no trainable ML model was implemented or trained.

## Device migration status

Migration validation passed. See `reports/device_migration_validation.md`.

## Research objective

To quantify predictive performance of simple historical rules and the RTS-GMLC provided day-ahead forecast before trainable ML models are introduced.

## Baselines implemented

- H1: `H1_PERSISTENCE`, `H1_DAILY_SEASONAL_PERSISTENCE`, and `H1_WEEKLY_SEASONAL_PERSISTENCE`.
- H24: `H24_DAILY_PERSISTENCE`, `H24_WEEKLY_SEASONAL_PERSISTENCE`, and external `RTS_DAY_AHEAD`.
- All operate by explicit timestamp lookup and validate historical source availability at or before forecast origin.

## H24 duplicate/equivalence handling

For a fixed H24 horizon, persistence at forecast origin equals target-minus-24-hour daily seasonal persistence. It is reported once as `H24_DAILY_PERSISTENCE`.

## RTS DAY_AHEAD benchmark

The canonical aligned DAY_AHEAD series was evaluated as an external H24 benchmark for load, wind, and utility-scale PV. Its issuance time is not represented as a proven exact 24-hour lead.

## Targets and rolling-origin folds

LOAD, WIND, and PV were evaluated independently over six expanding May--October validation folds and the September--October aggregate validation holdout.

## Validation-period results

| Target | Horizon | Best historical baseline (MAE) | RTS DAY_AHEAD MAE |
| --- | ---: | ---: | ---: |
| Load | H1 | H1_PERSISTENCE (178.419) | n/a |
| Wind | H1 | H1_PERSISTENCE (79.227) | n/a |
| PV | H1 | H1_DAILY_SEASONAL_PERSISTENCE (33.765) | n/a |
| Load | H24 | H24_DAILY_PERSISTENCE (211.392) | 126.613 |
| Wind | H24 | H24_DAILY_PERSISTENCE (586.542) | 269.006 |
| PV | H24 | H24_DAILY_PERSISTENCE (33.765) | 48.795 |

The full MAE, RMSE, sMAPE, nMAE, and nRMSE tables are in `artifacts/research_tables/baseline_validation_results.csv` and `reports/tables/baseline_validation_results.md`.

## Best validation baseline by target/horizon

By the frozen MAE criterion, H1 references are H1 persistence for load/wind and H1 daily seasonal persistence for PV. For H24, the best naive historical baseline is daily persistence for all three targets; across the full H24 benchmark group RTS DAY_AHEAD has lower MAE for load and wind, while daily persistence has lower MAE for PV.

## Fold stability

Fold MAE variation is documented in `artifacts/experiments/baselines/phase_06/metrics/baseline_fold_stability.csv` and the fold table. It is descriptive temporal variation, not stochastic variance.

## Final test accessed?

**NO.** The November--December final test remains locked and the runner exposes no casual test option.

## Research tables and figures

- `artifacts/research_tables/baseline_validation_results.csv`
- `artifacts/research_tables/baseline_fold_results.csv`
- `reports/tables/baseline_validation_results.md`
- `reports/tables/baseline_fold_results.md`
- Five figures and manifest under `artifacts/research_figures/phase_06/`

## Evidence registry entries

`E-BL-001` through `E-BL-006` register definitions, predictions, results, external benchmark, stability, and final-test isolation.

## Data and protocol integrity

RTS source verification passed. Processed and feature artifacts remained unchanged. Protocol freeze SHA-256 remains `666eb745de5ae01ba2033e825a4c6b0ba0cea1f9574c32426de8a5996581c0f9`.

## Environment

See `artifacts/environment/phase_06_environment.txt`.

## Tests

`.venv\\Scripts\\python.exe -m pytest`: **43 passed, 0 failed, 0 skipped**. `compileall -q src scripts tests` passed. No pytest warnings were reported.

## Limitations

Results are development/validation only; one RTS-GMLC year and undocumented DAY_AHEAD issuance semantics limit inference. Fold variation may reflect seasonal conditions. No significance testing was run.

## Phase 7 readiness

**READY.** All tests pass, baseline artifacts reproduce, final test remains locked, and the protocol freeze is unchanged.
