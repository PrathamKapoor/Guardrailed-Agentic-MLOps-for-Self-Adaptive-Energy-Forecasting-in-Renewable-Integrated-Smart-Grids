# Final frozen evaluation (Phase 19)

## Scope and authorization

Phase 19 is the first and only phase authorized to read the locked test partition
(2020-11-01 → 2020-12-31, 1464 hourly rows per target). All access passes through
`AccessMode.FINAL_EVALUATION` with `configuration_frozen=True`
(`smartgrid_mlops/experimental_design/protocol.py`) and
`smartgrid_mlops/final_evaluation/engine.authorize_final_evaluation`; every test
timestamp is verified against the frozen plan SHA-256 before any model code runs.
No training, HPO, feature selection, model selection, or retraining on test data
was performed; the engine loads its models and feature specifications from
frozen artifacts (Phase 9 best configs, Phase 10 ablation protocol, Phase 10
selected feature freeze, and the Phase 11 finalist registry).

## Frozen protocol

`artifacts/experimental_design/phase_19_final_evaluation_protocol_freeze.yaml`
was created and SHA-256-frozen (`79053d6faab827806f4f8d4f6b7915888e0e6ed34c736d230a3824492e5b99a5`)
before any official execution. The phase re-uses the existing frozen plan
`artifacts/experimental_design/final_test_comparison_plan.yaml` as the
authoritative comparison plan; its SHA-256 is also verified before evaluation.

## Final models (frozen finalists, Phase 11)

| Target | Candidate ID                       | Model                  | Feature set  | B_lags_only columns       |
| ---    | ---                                | ---                    | ---          | ---                       |
| load   | P10-load-random_forest-B_lags_only  | random_forest          | B_lags_only  | [lag_1, lag_24, lag_168]  |
| wind   | P10-wind-hist_gradient_boosting-B_lags_only | hist_gradient_boosting | B_lags_only | [lag_1, lag_24, lag_168] |
| pv     | P10-pv-random_forest-B_lags_only   | random_forest          | B_lags_only  | [lag_1, lag_24, lag_168]  |

External benchmarks (frozen, do not introduce alternatives):

- LOAD / WIND: RTS_DAY_AHEAD (`day_ahead_system_load` and `day_ahead_wind` columns
  of the canonical research index, observed in the source dataset).
- PV: H24_DAILY_PERSISTENCE (forecast at t = actual observed at t − 24 hours).

## Dataset split

- Final-test partition: 2020-11-01T00:00:00 to 2020-12-31T23:00:00, 1464 rows
  per target. Excluded from every prior phase.
- Engine uses the walk-forward convention continuing F01..F10: the training
  cutoff for fold F11 (November) is 2020-11-01 (no test timestamps leak in);
  for F12 (December) it is 2020-12-01. Models are reconstructed on the
  growing historical window (no November/December targets in training), then
  asked to predict the evaluation window — this is inference, not training.
- Single-year temporal coverage (2020 only) is a documented limitation.

## Evaluation procedure

1. Verify frozen plan SHA-256 (`final_test_comparison_plan.yaml`).
2. Verify the Phase 19 protocol freeze SHA-256.
3. For each target, run the engine:
   - Reconstruct the frozen reference model on the historical window
     (no HPO; no feature selection).
   - Reconstruct the frozen MLP challenger (E_full feature set, five seeds,
     deterministic algorithms).
   - Compute the day-ahead or daily-persistence baseline.
4. Compute per-fold and aggregate MAE, RMSE, sMAPE, nMAE, nRMSE.
5. Diebold-Mariano pairwise comparison (h-1 = 23 lag) and Holm-Bonferroni
   step-down across the three primary hypotheses (FT-H1-LOAD/WIND/PV).
6. MLflow run with `evidence_status = FINAL_EVALUATION_VALID` and
   `final_test_performance_access = AUTHORIZED_FROZEN_PLAN_EXECUTION`.

## Metrics

Primary: MAE. Secondary: RMSE, sMAPE, nMAE, nRMSE. Reported per target and per
configuration (frozen reference, MLP challenger, external benchmark). Benchmark
comparison: absolute and relative (percentage) MAE difference.

## Limitations

- Single dataset (RTS-GMLC, one leap year, 2020 only).
- Synthetic drift and simulated operational workflows in earlier phases.
- No production deployment; no live operator study; simulated decision cost.
- External benchmark semantics: under unmodified targets the RTS day-ahead
  is a stronger short-horizon forecast than development ML models; the
  benchmark row in the comparison table is therefore informative, not the
  goal of the system.
- Final-test is a single 2-month window; generalization beyond November/December
  2020 is unobserved.
- The PV baseline (H24 daily persistence) is naturally hard to beat at H24
  because of nocturnal zero-generation clipping, which raises sMAPE; the MAE
  comparison is the primary statistic.

## Registered analyses only

The spec forbids new statistical tests. We report: (a) error distributions
per target (figures), (b) primary metric MAE on the final-test window
(`final_forecasting_results.csv`), (c) pairwise model-vs-baseline comparison
(`final_model_comparison.csv`), and (d) the Diebold-Mariano + Holm-Bonferroni
families already produced by the engine (`holm_bonferroni.json`). No
additional hypothesis tests are introduced.
