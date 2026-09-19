# Phase 09 completion report

## Status

**PHASE 9 COMPLETE — H24 VALIDATION ONLY.** P9-DEV-001 and P9-DEV-002 are **RESOLVED**. The invalid neural implementation was sklearn `MLPRegressor`; it is quarantined/excluded from official evidence. The corrected implementation is PyTorch `PYTORCH_MLP_V1`; implementation consistency is **PASS**. Post-HPO validation completed **30 / 30** runs and official invalid evidence count is **0**.

FINAL_TEST_MODELING_ACCESS = **NO**. FINAL_TEST_PERFORMANCE_EVALUATION = **NO**. FINAL_TEST_MODEL_SELECTION_ACCESS = **NO**. FINAL_TEST_HPO_ACCESS = **NO**. FINAL_TEST_INTEGRITY_AUDIT_ACCESS = **YES** (`integrity_access_reason = P9-DEV-002`). The controlled integrity audit emitted no target values, predictions, errors, or final-test metrics.

## Evidence and protocol gates

- Post-HPO structural gate: PASS — three targets, F05/F06 only, five predefined seeds, 30 unique target×fold×seed runs.
- Evidence filtering: PASS — the official status policy accepts only `VALID`; neural evidence additionally requires `pytorch` / `PYTORCH_MLP_V1`. The exclusion regression tests cover invalid sklearn, smoke, audit-only, and a wrongly-labelled VALID sklearn record.
- Best configs and selected-config freeze: PASS — selected-config SHA-256 `37198a14a057a861362a66af2fdae7b7b7c06616d53c3781f3a5f70dcf2805b5` matches its recorded checksum.
- Protocol integrity: PASS — Phase 5 `666eb745…`, Phase 7 `7bcce9f…`, Phase 8 `6b2668e…`, and Phase 9 `db08e2b…` match their freeze records.
- Final-test audit: PASS — no November–December Phase 9 prediction, metric, trial, table, figure-source evidence, model access, or model-development workflow was used. P9-DEV-002 performed one authorized integrity-only reconstruction and exact feature comparison.

SEARCH MAE is F01–F04. POST-HPO MAE is `mean(F05 mean MAE, F06 mean MAE)`. Within-fold seed standard deviation is separately recorded in `artifacts/research_tables/hpo_post_hpo_seed_stability.csv`; it is not combined with fold variation.

## H24 results

### Load

Best naive MAE: 211.392. RTS DAY_AHEAD MAE: 126.613.

Untuned classical: random forest, MAE 179.458 (retrospective F01–F06). Tuned classical: random forest, SEARCH MAE 389.306; POST-HPO MAE N/A (no approved classical F05/F06 evaluation artifact exists). Untuned PyTorch MLP matched F05/F06 MAE: 294.864. Tuned PyTorch MLP: SEARCH MAE 773.668; POST-HPO MAE 320.234; relative PyTorch tuning improvement −8.604%. The valid post-HPO candidate is PyTorch MLP (320.234), because it is the only Phase 9 candidate with frozen F05/F06 evaluation evidence.

### Wind

Best naive MAE: 586.542. RTS DAY_AHEAD MAE: 269.006.

Untuned classical: hist-gradient boosting, MAE 513.907 (retrospective F01–F06). Tuned classical: SEARCH MAE 570.656; POST-HPO MAE N/A. Untuned PyTorch MLP matched F05/F06 MAE: 518.731. Tuned PyTorch MLP: SEARCH MAE 502.301; POST-HPO MAE 522.112; relative PyTorch tuning improvement −0.652%. The valid post-HPO candidate is PyTorch MLP (522.112).

### PV

Daily persistence MAE: 33.765. RTS DAY_AHEAD MAE: 48.795.

Untuned classical: random forest, MAE 36.588 (retrospective F01–F06). Tuned classical: SEARCH MAE 49.003; POST-HPO MAE N/A. Untuned PyTorch MLP matched F05/F06 MAE: 49.255. Tuned PyTorch MLP: SEARCH MAE 224.264; POST-HPO MAE 55.611; relative PyTorch tuning improvement −12.902%. Tuned classical beat daily persistence: NO (search-only comparison). Tuned PyTorch beat daily persistence: NO. Tuned candidates beat RTS DAY_AHEAD: NO for the PyTorch post-HPO comparison; the classical comparison is search-only.

## Runtime, boundaries, and physical validity

Valid trials: 30; invalidated audit trials: 15; pruned: 0; failed: 0. Classical HPO runtime: 49.235 s. Valid PyTorch HPO runtime: 13.922 s. Post-HPO runtime: 50.789 s. Quarantined sklearn runtime (audit-only): 80.152 s.

The selected PyTorch parameters are interior selections: hidden width 68; dropout 0.3803 (near, but not at, upper bound 0.4); learning rate 0.001752; weight decay 0.00003908. No boundary hit expands the frozen search.

Negative predictions / total predictions were load 0/7,320 (0%), wind 1/7,320 (0.0137%), and PV 1,101/7,320 (15.041%); NaN and Inf counts were zero for every target. Values were not clipped.

## Closure verification

The post-HPO validation results indicate that the selected PyTorch configurations did not achieve lower matched F05/F06 MAE than untuned PyTorch MLPs for these targets. The improvement observed on the search folds did not persist as a lower post-HPO MAE for the corrected PyTorch candidates. This is validation evidence only and is not a final-test conclusion.

Official tables and figures were regenerated from valid-only evidence; evidence registry correction: PASS; P9-DEV-001 resolution: PASS. P9-DEV-002 resolution: PASS — manifest staleness, with exact logical equivalence and reproducible current binary serialization established. The feature manifest preserves its historical binary checksum alongside the current binary checksum and logical-content fingerprint. Repository tests, compile, RTS, processed-data, feature logical integrity, experiment feature provenance, and protocol checks all pass. Phase 10 readiness: **READY**. Phase 10 was not begun.

Final closure commands: `.venv\Scripts\python.exe -m pytest` (**56 passed, 0 failed**); `.venv\Scripts\python.exe -m compileall -q src scripts tests` (PASS); `.venv\Scripts\python.exe scripts\bootstrap_rts_gmlc.py --verify-only` (PASS). Feature binary integrity: **REPAIRED / VERSIONED**; feature logical integrity: **PASS**; feature pipeline reproducibility: **PASS**; experiment feature provenance: **PASS**.
