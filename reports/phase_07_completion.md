# Phase 07 completion report

## Phase status and objective

**COMPLETE — UNTUNED VALIDATION.** The objective was to determine whether fixed conventional regressors improve validation forecasts relative to Phase 6 baselines, isolating model family effect without HPO, feature ablation, agentic selection, deep learning, or final-test access.

## Pre-phase status and protocol

The pre-phase suite passed: **43 passed, 0 failed, 0 skipped, 0 warnings**. The Phase 5 protocol SHA-256 remains `666eb745de5ae01ba2033e825a4c6b0ba0cea1f9574c32426de8a5996581c0f9`. The pre-result Phase 7 model protocol is frozen at SHA-256 `7bcce9f646d8c3758a5341a0ada91ac6c9bfe699aba8906788055b4050c330b7`.

## Models, features, scaling, folds, and seeds

Linear Regression, Ridge, Random Forest, Extra Trees, and HistGradientBoosting were evaluated using Phase 4 `combined_v1`. Ridge applies StandardScaler inside each training-fold pipeline; tree models are unscaled. Six expanding folds were fitted afresh. Random Forest and Extra Trees used seeds 42, 123, 2020, 2025, and 31415; the other fixed configurations ran once.

## Validation results and best untuned models

| Target | H24 best classical model | MAE | Beat best naive baseline? | Beat RTS DAY_AHEAD? |
| --- | --- | ---: | --- | --- |
| Load | Random Forest | 179.458 | YES | NO |
| Wind | HistGradientBoosting | 513.907 | YES | NO |
| PV | Random Forest | 36.588 | NO | YES |

For H1, the lowest validation MAE was Linear Regression for load (58.313), Extra Trees for wind (72.012), and HistGradientBoosting for PV (24.964). These are validation selections only.

## Baseline comparison

H24 best-naive MAEs were 211.392 (load), 586.542 (wind), and 33.765 (PV). External RTS DAY_AHEAD MAEs were 126.613, 269.006, and 48.795 respectively. The results indicate target-specific model ranking; no significance claim is made.

## Fold and seed stability

Fold metrics and seed-level MAEs are stored separately, avoiding conflation of temporal variation with stochastic seed variation.

## Descriptive error analysis

Validation error slices by hour, month/fold, output quartile, and target-specific conditions (higher load, wind generation bands, and PV nighttime/low/high output) are retained in `artifacts/experiments/classical/phase_07/diagnostics/error_slices.csv`. These are descriptive only.

## Runtime and physical validity

Mean per-fit training time ranged from approximately 0.014 s (Linear Regression) to 0.903 s (HistGradientBoosting) on this execution environment. Raw prediction diagnostics retained negative values: notable negative PV predictions occurred for Linear/Ridge/HistGradientBoosting; no clipping was applied.

## Artifacts and evidence

Prediction sequence, metrics, diagnostics, manifests, and figures are under `artifacts/experiments/classical/phase_07/` and `artifacts/research_figures/phase_07/`. H24/H1 tables, fold and seed tables, and runtime table are generated. Evidence entries `E-ML-001` through `E-ML-007` were added.

## Final-test isolation and integrity

**Final test accessed: NO.** RTS verification, processed/feature integrity tests, and protocol checks remained valid. Phase 6 artifacts were restored to their complete configuration after correcting a test side effect.

## Full tests and Phase 8 readiness

Post-phase suite: **48 passed, 0 failed, 0 skipped, 0 warnings**. Compilation passed. **Phase 8 readiness: READY** for explicit next-phase instructions only.
