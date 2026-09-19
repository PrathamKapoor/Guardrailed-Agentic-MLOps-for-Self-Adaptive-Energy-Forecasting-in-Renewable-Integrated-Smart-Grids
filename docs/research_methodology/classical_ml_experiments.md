# Classical ML experiments

## Classical Model Selection

RQ-ML-1 evaluates classical models against temporally valid baselines; RQ-ML-2 evaluates H24 against the strongest relevant benchmark; RQ-ML-3 considers target-specific ranking. Hypotheses H-ML-1 through H-ML-3 were recorded before results.

## Fixed Untuned Configuration

Linear Regression, Ridge, Random Forest, Extra Trees, and Histogram Gradient Boosting were specified in `classical_untuned_v1.yaml` before experiment execution. No search, optimization, AutoML, or agentic selection was performed.

## Feature Configuration

Every target and horizon uses the Phase 4 `combined_v1` feature configuration: calendar/cyclical, lag, rolling-history, and ramp inputs. DAY_AHEAD remains excluded from model inputs.

## Scaling Strategy

Ridge uses a StandardScaler inside its training-fold pipeline. Linear and tree models use the raw leakage-safe features; tree models are not scaled. Targets retain their native MW scale.

## Rolling-Origin Training and Seed Policy

All six frozen expanding folds are fitted afresh. Linear, Ridge, and HistGradientBoosting are treated as deterministic fixed configurations and run once; Random Forest and Extra Trees run with all five preregistered seeds. Seed variation is summarized within each fold separately from temporal fold variation.

## Evaluation and Baseline Comparisons

MAE, RMSE, zero-safe sMAPE, nMAE, and nRMSE reuse Phase 5 formulas. Baseline reference timestamps match the corresponding feature matrices. H24 uses the best Phase 6 naive baseline plus separate RTS DAY_AHEAD comparison where applicable.

## Computational Measurements and Physical Validity Checks

Per-fit training/prediction duration and available complexity metadata are stored. Raw predictions are scored without clipping; negative predictions and values above the observed validation maximum are reported as diagnostics.

## Final-Test Isolation and Limitations

Execution rejects November--December targets and exposes no test-unlock option. These are untuned, validation-only results from one RTS-GMLC year; rankings may change after optimization or external validation.
