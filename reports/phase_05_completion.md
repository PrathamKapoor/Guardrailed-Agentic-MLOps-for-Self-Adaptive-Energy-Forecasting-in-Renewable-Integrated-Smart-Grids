# Phase 05 completion report

**Phase status:** COMPLETE

## Pre-phase validation

The required pre-phase full suite was run before Phase 5 implementation: **21 passed, 0 failed, 0 skipped**. One Phase 4 documentation discrepancy was found: `docs/research_methodology/threats_to_validity.md` was required by the Phase 5 reading list but absent despite Phase 4 being marked complete. It was created during this phase. Pytest 9.1.1 was installed in the project-local `.venv` to run the mandated suite.

## Research objective and forecasting protocol

RQ-EXP-1 defines a leakage-free temporal evaluation protocol before model results. The primary horizon is **H24** and the secondary/diagnostic horizon is **H1**. Split membership is determined exclusively by `target_timestamp`:

- Training: 2020-01-01 00:00 through 2020-08-31 23:00
- Validation: 2020-09-01 00:00 through 2020-10-31 23:00
- Final test: 2020-11-01 00:00 through 2020-12-31 23:00 — **LOCKED**

Historical feature context from an earlier partition remains permitted when its source timestamp is no later than forecast origin. Random KFold, shuffled train/test splitting, and stratified random folds are prohibited.

## Actual holdout sample counts

| Target | Horizon | Train | Validation | Locked test |
| --- | ---: | ---: | ---: | ---: |
| Load | H1 | 5,687 | 1,464 | 1,464 |
| Load | H24 | 5,664 | 1,464 | 1,464 |
| Wind | H1 | 5,687 | 1,464 | 1,464 |
| Wind | H24 | 5,664 | 1,464 | 1,464 |
| PV | H1 | 5,687 | 1,464 | 1,464 |
| PV | H24 | 5,664 | 1,464 | 1,464 |

Counts were computed from the six feature Parquet matrices, not inferred from theoretical calendar lengths.

## Rolling-origin protocol

Six expanding-window folds were generated for every target/horizon (36 concrete fold records). Training begins with available January history and expands through the month before each May–October validation block. H24 fold training counts are 2,712, 3,456, 4,176, 4,920, 5,664, and 6,384; validation counts are 744, 720, 744, 744, 720, and 744. H1 training counts are 23 higher in every fold due to its earlier first usable target. Every fold satisfies `max(train target_timestamp) < min(validation target_timestamp)`, and every validation timestamp precedes November.

## Metrics, seeds, and statistical analysis

- Primary selection metric: MAE.
- Secondary metrics: RMSE, sMAPE, nMAE, nRMSE.
- Normalization denominator: mean absolute observed target for both normalized metrics.
- PV: standard MAPE is not primary because legitimate zeros make it unstable; the zero-safe sMAPE convention is explicit.
- R²: descriptive only, never the sole selection criterion.
- Stochastic seeds: `[42, 123, 2020, 2025, 31415]`; deterministic implementations run once unless randomness exists.
- Primary paired comparison plan: Diebold–Mariano with horizon-appropriate autocorrelation-aware variance.
- Secondary nonparametric comparison: Wilcoxon signed-rank where assumptions permit.
- Significance: α=0.05; Holm–Bonferroni for related multiple comparisons.
- Practical effect: relative MAE/RMSE improvement; future dependent intervals use a documented block bootstrap.

No metrics were evaluated on forecast results and no statistical tests were run in Phase 5.

## Final-test isolation

**PASS.** `MODEL_SELECTION` cannot request TEST targets. `FINAL_EVALUATION` exposes TEST only after `configuration_frozen=True`. A mandatory boundary test proves that an H24 sample with origin 2020-10-31 and target 2020-11-01 belongs to TEST. No test performance was inspected.

## Protocol freeze

- Artifact: `artifacts/experimental_design/protocol_freeze.yaml`
- SHA-256: `666eb745de5ae01ba2033e825a4c6b0ba0cea1f9574c32426de8a5996581c0f9`
- Protocol version: `rts_gmlc_exp_protocol_v1`
- Feature manifest SHA-256: `0e46baae741f41da7cfdad57c94d66881df368638412837a019e4f4c22b800ee`
- Model results observed when frozen: false

## Research artifacts

- Six target/horizon split manifests and `rolling_origin_folds.yaml`
- Versioned experiment configs under `config/experiments/`
- `docs/research_methodology/experimental_design.md`
- `docs/research_methodology/statistical_analysis_plan.md`
- `docs/research_methodology/experiment_naming.md`
- Updated methodological decisions, threats to validity, progress, and evidence registry
- Paper tables for temporal holdout, rolling origins, and metrics
- `artifacts/research_figures/phase_05/temporal_evaluation_design.png` and manifest

## Tests and integrity

Commands:

```bash
.venv/bin/python -m pytest
.venv/bin/python -m compileall -q src scripts tests
python3 scripts/bootstrap_rts_gmlc.py --verify-only
```

Final result: **33 passed, 0 failed, 0 skipped, 0 pytest warnings**. Python compilation passed. Raw RTS-GMLC integrity/manifest/checksums PASS. Every canonical Phase 3 Parquet checksum still matches `processed_dataset_manifest.yaml`. Split generation is deterministic across repeated runs. Project Git metadata remains absent, so a project commit SHA is unavailable.

## Limitations and Phase 6 readiness

Only one test-system year is available; the two-month final test is not universally representative; repeated use of validation folds can still induce development overfitting; no weather features are present; many later comparisons require multiplicity control and external validation. **Phase 6 readiness: READY** for baseline implementation under the frozen protocol. Phase 5 trained no baseline or ML model and performed no hyperparameter optimization.
