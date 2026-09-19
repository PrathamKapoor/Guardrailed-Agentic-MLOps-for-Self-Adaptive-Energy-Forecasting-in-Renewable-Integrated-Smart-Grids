# Final-Test Evaluation Methodology (Phase 19)

## Purpose

Locked-partition evaluation of the frozen forecasting configurations selected
during development, executed once, after the configuration freeze, under the
`FINAL_EVALUATION` access mode.

## Data and partitions

- Dataset: RTS-GMLC 2020 canonicalized hourly series (`data/processed/`),
  feature matrices `combined_v1` at horizon 24
  (`data/processed/features/{load,wind,pv}/h24/combined_v1.parquet`).
- Locked test partition: target timestamps 2020-11-01 .. 2020-12-31.
- Evaluation folds: monthly walk-forward F11 (November) and F12 (December),
  the direct continuation of the development fold design. For each fold the
  training window is all history strictly before the month start (train +
  validation partitions only); no test timestamp ever enters any training
  window.

## Configurations (all frozen before execution)

- Reference models: per-target winners recorded in
  `artifacts/experimental_design/final_test_comparison_plan.yaml`, with
  hyperparameters taken verbatim from
  `artifacts/experimental_design/phase_10_ablation_protocol_freeze.yaml`
  (LOAD: random forest; WIND: histogram gradient boosting; PV: random forest).
- Challenger: `PYTORCH_MLP_V1` with phase-09 HPO best configurations per
  target; five master seeds aggregated by mean prediction, replicating the
  phase-10 confirmation training procedure (StandardScaler on features and
  target fitted on the outer training window only, chronological inner tail,
  maximum 12 epochs, early-stopping patience 4).
- Baseline comparators: external `RTS_DAY_AHEAD` forecasts from the
  canonicalized processed columns for LOAD and WIND; `H24_DAILY_PERSISTENCE`
  (actual value observed 24 hours earlier) for PV.

## Statistical protocol

- Primary metric: MAE. Full metric set also computed (RMSE, sMAPE, nMAE,
  nRMSE).
- Primary hypotheses FT-H1-{LOAD,WIND,PV}: frozen reference vs its baseline
  comparator, two-sided Diebold-Mariano tests on absolute-error differentials
  with Newey-West variance (maximum lag = h-1 = 23), normal approximation.
- Multiple-testing control: Holm-Bonferroni step-down across the three primary
  hypotheses at alpha = 0.05.
- Secondary (uncorrected, descriptive): reference vs challenger comparison.

## Governance constraints

- Test-partition access requires `configuration_frozen=True`; every consumed
  test timestamp passes through the deterministic authorization gate.
- The frozen plan artifact is checksum-verified and never modified.
- No model selection, threshold tuning, or configuration change may be derived
  from these results.

## Reproducibility

Run via `scripts/run_phase19_final_evaluation.py --execute`. Deterministic
seeds throughout; see `reports/phase_19_final_execution_report.md` for the
recorded determinism check, environment details, and limitations.
