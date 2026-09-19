# Future Experiments — Preregistered Design

Status: DESIGN ONLY — NOT EXECUTED. Preregistration required before data access.

This document defines how the recommended transfer experiments should be designed WITHOUT contaminating the already-completed Phase 19 and external validation evaluations. All experiments below must be recorded as new phases with frozen plans before any external data beyond OPSD DE (already used) is accessed for them.

## General Constraints (applies to all)

- **Frozen components:** Feature definitions B_lags_only/E_full per `config/ablation/phase_10.yaml`, model families (RF/HGB/MLP), horizon H24, metric definitions per `statistical_analysis_plan.md`. No architecture or feature-set changes unless explicitly declared as new independent variable.
- **Allowed training data:** RTS TRAIN+VALIDATION (7128 samples) for baseline frozen evaluation; for adaptation experiments, training may additionally include a defined external training split that is disjoint from its evaluation split and never includes the external test period.
- **Forbidden:** Post-hoc selection of best model/threshold after seeing evaluation metrics; altering Phase 19 plan (`final_test_comparison_plan.yaml` sha `afb77163...`); revisiting locked RTS TEST; tuning hyperparameters on evaluation data; fabricating data.
- **Evaluation protocol:** Metrics MAE primary + RMSE/sMAPE/nMAE/nRMSE secondary; DM Newey-West lag 23 + Holm-Bonferroni alpha 0.05 per family; missing handling as in external_validation protocol; sample counts and exclusions recorded.
- **Statistical tests:** Reuse `final_evaluation/engine.py` DM+Holm; success/failure criteria preregistered per experiment.
- **Reproducibility:** New dataset manifests with source/license/checksum, feature_version incremented (external_v2...), MLflow experiment `smartgrid/future/<name>`, artifact structure `artifacts/experiments/future/<name>/`.

---

## Experiment A: Scale-Normalized Transfer

- **Hypothesis:** Per-system target normalization (e.g., z-score using training-system mean/std or robust scaling) reduces scale-driven transfer error, improving nMAE on external DE without changing model structure.
- **Independent variable:** Scaling policy — baseline (no rescaling beyond StandardScaler fitted on RTS training applied forward) vs normalized (per-system mean/std computed on respective training system, applied to both training and external evaluation).
- **Dependent variables:** MAE, nMAE, RMSE, DM vs persistence (EXT-H1) on OPSD DE (same 49,983 samples) and on RTS TEST (1,464) to check within-distribution impact.
- **Frozen components:** Model hyperparameters, feature sets, seeds, evaluation folds.
- **Allowed training data:** RTS TRAIN+VALIDATION for both arms; normalization statistics computed only on that training data (for normalized arm, external scaling uses external training split statistics computed before evaluation, not including evaluation period).
- **Forbidden:** Tuning normalization type on evaluation performance; choosing best of many scalers post-hoc.
- **Evaluation protocol:** Same as external validation: single H24, all evaluable timestamps, persistence baseline, DM+Holm per target.
- **Statistical tests:** DM reference vs baseline and normalized-reference vs baseline; Holm across 3 targets per arm.
- **Success criteria:** Normalized arm shows statistically significant reduction in nMAE vs baseline arm on external, with Holm-controlled DM indicating normalized is not worse than persistence? Failure: no improvement or degradation.
- **Run condition:** Requires preregistered plan file `artifacts/experimental_design/future_scale_normalized_plan.yaml` with checksum before execution.

## Experiment B: Additional-Country Transfer

- **Hypothesis:** Transfer performance varies by country/grid composition; e.g., wind-rich vs solar-rich systems show different degradation patterns.
- **Independent variable:** Country (DE, FR, AT, IT, ES, etc., from OPSD 2020-10-06).
- **Dependent variables:** Same metrics per target per country; country-wise DM vs persistence.
- **Frozen components:** Same as A (no per-country tuning).
- **Allowed training data:** RTS TRAIN+VALIDATION only for inference; no per-country retraining.
- **Forbidden:** Selecting best country post-hoc as claim of generalizability; averaging across countries without reporting per-country breakdown.
- **Evaluation protocol:** Per-country canonicalization and feature building (same lag/calendar definitions) with country-specific actual columns (e.g., FR_load_actual...); each country evaluated independently with same H24, ≥720 samples required to be conclusive per country.
- **Statistical tests:** Per-country Holm families (3 hypotheses each); no cross-country pooling for significance.
- **Success criteria:** Descriptive: report per-country MAE and DM; success not defined as universal superiority but as pattern characterization (consistent vs degraded vs target-specific). Failure to meet sample threshold for a country = inconclusive for that country, not pooled.
- **Run condition:** Requires per-country manifests and feature artifacts before evaluation.

## Experiment C: Additional-Year Transfer

- **Hypothesis:** Interannual variation within same system (e.g., RTS-GMLC if new synthetic year released) tests temporal generalization better than single-year external.
- **Independent variable:** Year (2020 vs new synthetic year with different seed, if published by GridMod).
- **Dependent variables:** Same metrics, year-wise.
- **Frozen components:** Same.
- **Allowed training data:** 2020 TRAIN+VALIDATION for training; new year only for evaluation (no training on new year).
- **Forbidden:** Mixing years for training without declaring as new independent variable.
- **Evaluation protocol:** Same H24, hourly, missing handling as before; requires that new year's data be generated independently (different random seed) and manifest recorded.
- **Statistical tests:** Per-year Holm families.
- **Success criteria:** Same as B — descriptive pattern, not pooled.
- **Run condition:** Blocked until upstream RTS-GMLC releases additional year; currently no such data exists locally (verified 2026-08-26).

## Experiment D: Target-Specific Adaptation

- **Hypothesis:** PV, which showed best relative transfer (reference 4038 vs persistence 1060, least worst ratio), may benefit from target-specific handling (e.g., nighttime zero handling or PV-specific feature subset) while LOAD does not.
- **Independent variable:** Feature subset per target (e.g., PV uses B_lags_only vs E_full vs PV-optimized subset preregistered).
- **Dependent variables:** Per-target MAE and DM vs persistence.
- **Frozen components:** Model families frozen, but feature subset is now the experimental factor (preregistered).
- **Allowed training data:** RTS TRAIN+VALIDATION.
- **Forbidden:** Selecting feature subset after seeing external PV performance.
- **Evaluation protocol:** Same H24, per-target evaluation on OPSD DE PV vs LOAD/WIND.
- **Statistical tests:** Per-target DM, Holm across 3.
- **Success criteria:** Preregistered: PV-optimized subset shows significant improvement over B_lags_only on external PV (DM p<0.05/3) without degrading LOAD/WIND beyond non-significance.
- **Run condition:** Requires preregistered feature subset definitions in new config file with checksum.

## Post-Hoc Explanation vs Preregistered

- **Preregistered future work:** All of A-D above, when executed after plan filing and before data access for that experiment.
- **Post-hoc explanation:** Any analysis of *why* German load shape differs, attribution to coal/gas mix, weather, etc., performed after seeing external results without preregistration — must be labeled exploratory, not confirmatory, and must not be presented as hypothesis test.

## Governance

All future experiments remain evaluation-only; no promotion/deployment triggered by results; deterministic gates authoritative; manifests required before data use per `AGENTS.md`.

