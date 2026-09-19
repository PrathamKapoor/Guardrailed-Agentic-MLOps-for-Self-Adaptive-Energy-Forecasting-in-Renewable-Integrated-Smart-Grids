# EXTERNAL DATASET + VALIDATION REPORT

## Executive Summary

Acquired Open Power System Data (OPSD) Time Series 2020-10-06 (hourly, 60min singleindex, 125 MB, CC BY 4.0) as a genuinely external electricity system (German DE load/wind/solar 2015-2020) independent of RTS-GMLC 2020 synthetic. Validated, canonicalized, and feature-engineered 50,295 hourly observations into leakage-safe H24 feature matrices (50,103 rows). Evaluated frozen Phase 19 configurations (LOAD RF, WIND HGB, PV RF + MLP challenger) trained on RTS TRAIN+VALIDATION without retuning, on 49,983 external evaluable samples per target. Results show poor transferability: persistence baseline significantly outperforms all frozen models on this external German scale, indicating strong distribution shift — not a bug to fix. All artifacts versioned, MLflow logged to `smartgrid/external_validation` (3 FINISHED runs), determinism verified (max relative deviation 0), Phase 19 untouched.

## Candidate Datasets Considered

- **GEFCom2012/2014 Load:** 2004-2008/2006-2014 hierarchical load, wind track, hourly, but supplementary data via ScienceDirect paywall/Dropbox, no explicit stable licensed URL, temperature covariate mismatch, PV absent in 2012. Fails on reproducible official-source licensing.
- **PJM Hourly Metered Load (Data Miner 2):** 1993-present hourly per load area, load only, requires account/API for bulk, no wind/PV in same feed, Grid Status mirror is third-party not official. Fails on wind/PV absence and official-source reproducibility.
- **OPSD Time Series 2020-10-06:** Selected. See below.

Full comparison: `docs/external_dataset_candidate_evaluation.md`.

## Selected Dataset

**OPSD Time Series 2020-10-06** — `time_series_60min_singleindex.csv` (124 MB, 50,402 rows, hourly). Hourly load, wind, solar actuals for 32 European countries including DE. DOI 10.25832/time_series/2020-10-06.

## Why It Qualifies

- External system: European TSO actuals (ENTSO-E Transparency) vs US synthetic RTS-GMLC — different generation mix, temporal window (2015-2020 real vs 2020 synthetic), independent data generating process.
- Targets: all three present for DE (load, wind, solar) hourly — supports LOAD (required) + WIND + PV.
- Features: calendar + lag/rolling/ramp fully derivable without leakage; meets B_lags_only (lag_1/24/168) and E_full (12 features) requirements.
- Sampling: hourly start-of-interval UTC, >=720 samples (actually 50k), missing 0.19% <10% conclusive.
- License: CC BY 4.0 explicitly, reproducible official URL, versioned with hash.

## Provenance

- Source URL: https://data.open-power-system-data.org/time_series/2020-10-06/time_series_60min_singleindex.csv
- Publisher: Open Power System Data, Neon Neue Energieökonomik, Jonathan Muehlenpfordt
- Primary source: ENTSO-E Transparency Platform, processed via Python/pandas notebooks (MIT) at https://github.com/Open-Power-System-Data/time_series
- Retrieval: 2026-08-26T21:24:00Z, archive sha256 `6a7f2bc571314cbf9c321cc03437691cd4be95c3a6f075e60ff99e8035c704c8`, datapackage sha `2f4b7ae48e135...`, bytes 130862382, recorded in `data/manifests/opsd_time_series_manifest.yaml` (+ checksums file) with source/license/retrieval/version/schema/approval/archive_checksum.

## Acquisition

- `curl -L` from official URL to `data/external/opsd_time_series/time_series_60min_singleindex.csv` + `datapackage.json`, sha256 verified, no silent download without provenance. Raw RTS-GMLC untouched, isolated under `data/external/opsd_time_series/`.

## Manifest

- `data/manifests/opsd_time_series_manifest.yaml` (59 lines, now 70 with derived_artifacts) contains dataset, version, source, license, retrieval, archive/datapackage checksums, temporal coverage, target_mapping, feature_mapping, derived_artifacts checksums (canonical hourly 9eccac..., wind ac1b57..., pv e1151d..., research index afa95a..., features 209611... etc.), feature_version external_v1, provenance citation.
- `data/manifests/opsd_time_series_checksums.sha256` records raw file hash.

## Data Validation

- File checksum verified, schema header contains utc_timestamp + DE_* columns, 50,402 rows, 50,295 valid DE rows after dropping missing (2015-01-01 07:00 to 2020-09-30 23:00), 0 duplicates, span 50201 hours, missing 98 (0.19%) — conclusive. Sampling hourly UTC, duplicate check passed, target distributions: LOAD mean ~55000 MW, WIND ~11500, PV ~4500 (scale an order larger than RTS).

## Canonicalization

- Script `scripts/build_opsd_external.py` builds `data/processed/external/opsd_time_series/{load,wind,pv}_hourly.parquet` (timestamp + actual_*) and `research_hourly_index.parquet`, plus `features/{target}/h24/combined_v1.parquet` (50,103 rows, lag/rolling/calendar/ramp leakage-safe: forecast_origin = target_timestamp -24h, features from data <= origin). Reuses same lag definitions as `src/smartgrid_mlops/features/pipeline.py`. Checksums recorded: load hourly 9eccac..., features load 209611... etc., stored in manifest derived_artifacts.

## Feature Mapping

For every required feature:

- AVAILABLE DIRECTLY: none
- DERIVABLE WITHOUT LEAKAGE: hour_sin/cos, dow_sin/cos, doy_sin/cos (from utc_timestamp), lag_1/24/168, rolling_mean_24/168, ramp_1h (from prior actuals ≤ origin) — all 12 E_full features. Validated via `validate_feature_compatibility` for both B_lags_only and E_full.
- NOT AVAILABLE / SEMANTICALLY INCOMPATIBLE: none.

No feature invented; mapping documented in manifest feature_mapping and `docs/research_methodology/external_validation.md`.

## Frozen Model Configuration

Traced from `final_test_comparison_plan.yaml` (sha256 afb77163...) → `phase_10_ablation_protocol_freeze.yaml` (LOAD RF n_estimators 191, WIND HGB max_iter 111, PV RF 209) + `best_configs/*_pytorch_mlp.yaml` (MLP challenger). No recreation by tuning; models refit on RTS TRAIN+VALIDATION (7128 samples) with frozen hyperparameters/seed 42 via `final_evaluation.engine.fit_predict_*`, StandardScaler fitted on training only and applied forward to external features.

## External Evaluation

Executed via `src/smartgrid_mlops/external_validation/engine.py::evaluate_external` (inference-only) and runner `scripts/run_external_validation.py --dataset opsd_time_series --execute`:

- Training: RTS TRAIN+VALIDATION (7128 samples, all development before 2020-11-01)
- Evaluation: OPSD external evaluable rows (49,983 per target after persistence baseline filtering)
- Baselines: H24 daily persistence via `timestamp_lag_value` (actual at target-24h); RTS DAY_AHEAD not used externally (OPSD forecast columns exist but persistence is comparable baseline)
- MLflow: experiment `smartgrid/external_validation`, 3 runs FINISHED (EXT-opsd_time_series-{load,wind,pv}), params dataset/frozen_plan_sha/feature_version, metrics MAE/RMSE etc., artifacts summary.json

## Results

H24, 49,983 samples per target (external):

- LOAD: reference RF MAE 48,228 vs challenger MLP 30,283 vs baseline persistence 4,460 — baseline 10x better
- WIND: reference 10,141 vs challenger 9,154 vs baseline 5,944 — baseline best
- PV: reference 4,039 vs challenger 3,793 vs baseline 1,061 — baseline best

Full table: `artifacts/research_tables/external_validation_results.csv` and `artifacts/experiments/external_validation/opsd_time_series/official/metrics/external_metrics.csv` (RMSE/sMAPE/nMAE/nRMSE also).

## Statistical Analysis

Reused DM + Holm-Bonferroni (Newey-West lag 23, two-sided normal, alpha 0.05):

- EXT-H1-LOAD: DM +182.07 p 0.0 Holm reject
- EXT-H1-WIND: p 1.11e-91 reject
- EXT-H1-PV: p 0.0 reject (all three reject — references significantly worse than persistence)
- EXT-H2 reference vs challenger also p 0.0 (challenger significantly better than reference but still far from baseline)

n=49,983 large, assumptions appropriate.

## Reproducibility

Second independent run into `C:/Users/LENOVO/AppData/Local/Temp/opsd_rerun` produced max relative metric deviation 0.0, max absolute prediction deviation <2e-12 (MLP ULP). Dataset manifest + checksums + feature_version external_v1 + frozen plan sha + per-target hyperparameters + code version + env (Python 3.13.2, sklearn 1.6.1, torch, pyarrow 14, mlflow) + artifact structure `artifacts/experiments/external_validation/opsd_time_series/official/{metrics/manifests}` all versioned.

## Tests

- Existing external-validation tests 13/13 pass (synthetic fixtures test-only, no fake external results)
- Phase 19 tests 11/11 still pass; combined suite 24-27 tests green (including phase_00, bootstrap, data_audit)
- New external dataset revealed edge case: challenger requires E_full 12 features, fixed synthetic fixture to include all

## Phase 19 Integrity

- Phase 19 plan modified: NO (sha256 afb77163... matches sidecar)
- Phase 19 checksum changed: NO
- Phase 19 artifacts modified: NO (13,176 rows prediction parquet unchanged)
- Phase 19 predictions modified: NO
- Locked test set modified: NO
- Model tuning after Phase 19: NO

Verified via sha256sum and file existence checks after external validation.

## Research Integrity

- Raw RTS-GMLC modified: NO
- External dataset provenance recorded: YES (manifest + checksums)
- Synthetic data used as scientific validation: NO (synthetic only in tests, never presented)
- Scientific results fabricated: NO (all metrics from real OPSD inference)
- Quantum code imported: NO
- External project modified: NO (worked only in canonical `C:\Projects\guardrailed-agentic-mlops-smart-grid_trial`)

## Limitations

- Single external country (DE) — not universal; German scale mismatch (50 GW vs RTS 1-3 GW) explains poor transferability; recalibration not attempted per freeze.
- No external DAY_AHEAD comparator evaluated (OPSD forecast columns available but persistence chosen for comparability).
- Only H24 evaluated; no seasonal breakdown beyond full-period.
- No meteorological covariates (consistent with frozen feature sets).

## Recommended Next Phase

1. Investigate scale-invariant adaptation (e.g., per-system normalization) as separate preregistered experiment, not post-hoc tuning.
2. Extend external validation to additional OPSD countries/years using same frozen protocol and this infrastructure.
3. Retain Phase 19 and current external results as final evidence; any new model must go through governed promotion as challenger.

## Repository Integrity

WORKED ONLY IN:
C:\Projects\guardrailed-agentic-mlops-smart-grid_trial

Verification: git status shows untracked files only inside canonical; no files created/modified outside canonical except OS temp pytest dirs; external dataset isolated under `data/external/opsd_time_series/`; no sibling project touched.

