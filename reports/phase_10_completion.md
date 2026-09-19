# Phase 10 completion report

## Status

**PHASE 10 COMPLETE — CONTROLLED H24 FEATURE ABLATION.** The study addressed RQ-ABL-1 to RQ-ABL-4 using predefined Phase 4 feature-family projections and fixed Phase 9 model configurations. No HPO, retuning, final-test modeling, selection, or performance evaluation occurred.

Primary classical models were load Random Forest, wind HistGradientBoosting, and PV Random Forest. The secondary model was `PYTORCH_MLP_V1`. Development ranking used F01–F04; F05/F06 were post-ablation confirmation only. All feature subsets had identical common timestamp membership within fold (0 rows removed).

## Selections and confirmation

| Target | Classical selected set | F01–F04 MAE | F05–F06 mean MAE | MLP selected set | F01–F04 MAE | F05–F06 mean MAE |
| --- | --- | ---: | ---: | --- | ---: | ---: |
| Load | B_lags_only | 360.592 | 285.965 | E_full | 768.375 | 482.597 |
| Wind | B_lags_only | 527.033 | 528.613 | E_full | 508.619 | 532.417 |
| PV | B_lags_only | 48.005 | 44.066 | E_full | 240.730 | 244.112 |

Wind’s classical B selection was within 0.5% of the F01–F04 minimum and therefore used the preregistered fewer-feature tie-break. The complete set was not necessary for any primary classical selection, but remained selected for the three MLP anchor comparisons.

## Execution and controls

The smoke run was marked `NON_EVIDENCE_SMOKE`. Official F01–F04 execution produced 240 valid runs (60 classical, 180 MLP); confirmation produced 36 valid runs (6 classical, 30 MLP). Timestamp-level prediction/error sequences are retained. Tables, figures, common-sample manifest, selection freeze, and evidence registry were generated.

FINAL_TEST_TRAINING_ACCESS = NO; FINAL_TEST_HPO_ACCESS = NO; FINAL_TEST_MODEL_SELECTION_ACCESS = NO; FINAL_TEST_FEATURE_SELECTION_ACCESS = NO; FINAL_TEST_PERFORMANCE_EVALUATION = NO. Historical FINAL_TEST_INTEGRITY_AUDIT_ACCESS = YES, P9-DEV-002 only. Phase 11 readiness: READY; Phase 11 was not begun.

Final checks: `.venv\Scripts\python.exe -m pytest` reported **59 passed, 0 failed**; compile check PASS; RTS integrity PASS. Phase 10 protocol SHA-256 `92504862b2ddec71b242b7ed396547504743b7cd8b66aa038f880316ab35d257` and selected-feature freeze SHA-256 `243c65094bf35a974f671a28502cb9ac96c645f713ac048658a428cd376dc05d` match their recorded hashes.
