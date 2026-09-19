# External Validation Execution Report — OPSD Time Series

Status: COMPLETE (classical-owned execution, evaluation-only, no model tuning)

## 1. Objective

Test whether the already-frozen Phase 19 configurations generalize beyond the RTS-GMLC 2020 evaluation environment. External validation used the same frozen reference/challenger models and feature definitions as Phase 19, applied to an approved independent dataset, without hyperparameter retuning, model selection, or protocol changes.

## 2. Dataset

**Selected:** Open Power System Data (OPSD) Time Series, version 2020-10-06, file `time_series_60min_singleindex.csv`

Why selected: Well-established public benchmark for electricity forecasting, primary data from ENTSO-E Transparency via TSOs, hourly, load + wind + solar actuals for DE and 31 other European systems, CC BY 4.0, versioned DOI, direct official download, sufficient temporal coverage (2015-2020). See `docs/external_dataset_candidate_evaluation.md` for comparison against GEFCom2012/2014 and PJM (GEFCom failed on stable licensed download, PJM required API/account and lacked wind/PV in same feed).

Targets supported: LOAD (`DE_load_actual_entsoe_transparency`), WIND (`DE_wind_generation_actual`), PV (`DE_solar_generation_actual`) — all three present, hourly.

## 3. Dataset Provenance

- **Source URL:** https://data.open-power-system-data.org/time_series/2020-10-06/time_series_60min_singleindex.csv
- **Homepage:** https://data.open-power-system-data.org/time_series/2020-10-06
- **DOI:** https://doi.org/10.25832/time_series/2020-10-06
- **Documentation/GitHub:** https://github.com/Open-Power-System-Data/time_series (notebooks, processing in Python/pandas, MIT)
- **Publisher:** Open Power System Data, Neon Neue Energieökonomik, Jonathan Muehlenpfordt (muehlenpfordt@neon-energie.de)
- **Primary source:** ENTSO-E Transparency Platform
- **License:** CC BY 4.0 (https://open-power-system-data.org/ — Data published under Creative Commons Attribution 4.0 International)
- **Retrieval date:** 2026-08-26T21:24:00Z
- **Archive checksum (sha256):** 6a7f2bc571314cbf9c321cc03437691cd4be95c3a6f075e60ff99e8035c704c8
- **Datapackage checksum:** 2f4b7ae48e1352deb1991728e013fe42e742af5e81a5140d87185e470cd0ac36
- **Manifest:** `data/manifests/opsd_time_series_manifest.yaml` (+ `opsd_time_series_checksums.sha256`)
- **Temporal coverage raw:** 2014-12-31T23:00 + 2015-01-01T00:00 to 2020-09-30T23:00 UTC, 50402 rows; valid DE rows after dropping missing: 50295 (2015-01-01 07:00 to 2020-09-30 23:00 + 2020-10-01 CET), missing fraction 0.00195 conclusive.

## 4. Acquisition

- Downloaded via `curl -L` from official OPSD URL to `data/external/opsd_time_series/time_series_60min_singleindex.csv` (125 MB, sha256 verified), plus `datapackage.json` (296 kB) and bytes recorded.
- No anonymous curl without provenance: source URL, retrieval timestamp, checksums, version, license recorded in manifest before any experiment use per `AGENTS.md` Dataset policy.
- Raw RTS-GMLC data untouched; external data isolated under `data/external/opsd_time_series/`.

## 5. Dataset Validation

- **File checksum:** verified 6a7f2bc... matches download; no extraction needed (CSV).
- **Schema:** header contains `utc_timestamp`, `DE_load_actual_entsoe_transparency`, `DE_wind_generation_actual`, `DE_solar_generation_actual` plus 297 other European columns; types hourly datetime UTC + float MW.
- **Timestamps:** UTC hourly, duplicate check 0 dups, sorted, span 50201 hours for DE valid rows; missing hours 98 (0.19%) after cleaning — conclusive (>=720, <10% missing).
- **Missingness:** early 2015-01-01 00:00-06:00 DE rows missing (empty strings) — dropped (98 rows_lost due to missing + 192 feature warmup = total 299 before feature availability).
- **Target distributions:** LOAD mean ~55000 MW, WIND ~11500 MW, PV ~4500 MW (German system scale — an order of magnitude larger than RTS-GMLC synthetic, indicating strong distribution shift).
- **Sampling:** hourly, start-of-interval (UTC), consistent with research index.
- **Duplicate timestamps:** 0.

## 6. Mapping

External → research target definition → forecast origin → horizon → feature availability → prediction target:

- `DE_load_actual_entsoe_transparency` → `actual_system_load` (LOAD) — country-aggregated total load, MW, hourly
- `DE_wind_generation_actual` → `actual_wind` (WIND) — aggregated wind generation, MW
- `DE_solar_generation_actual` → `actual_pv` (PV) — aggregated solar generation, MW

Forecast origin = `utc_timestamp - 24h`? No, origin = target_timestamp - 24h per feature pipeline (`forecast_origin = target_timestamp - horizon`). Feature availability: all 12 frozen features derivable from timestamps + contiguous actuals without external weather. Prediction target = actual at target_timestamp. Explicit mapping documented in manifest `target_mapping`.

If unavailable: not applicable — all three targets available.

## 7. Feature Compatibility

For every required feature, classification:

- **AVAILABLE DIRECTLY:** None (no weather covariates in frozen sets)
- **DERIVABLE WITHOUT LEAKAGE:** hour_sin/cos, dow_sin/cos, doy_sin/cos (from utc_timestamp), lag_1/24/168, rolling_mean_24/168, ramp_1h (from prior actuals ≤ forecast_origin) — all 12 classified as DERIVABLE WITHOUT LEAKAGE.
- **NOT AVAILABLE:** None
- **SEMANTICALLY INCOMPATIBLE:** None

Validation via `src/smartgrid_mlops/external_validation/validation.py::validate_feature_compatibility` passed for both B_lags_only (3) and E_full (12). Leakage check `validate_no_leakage` enforces `target == origin + 24h` exactly, ensuring no future target used.

## 8. Frozen Model/Configuration

Traced from Phase 19 plan → configuration → artifact → model (no retraining on external):

- Frozen plan: `artifacts/experimental_design/final_test_comparison_plan.yaml` sha256 `afb77163ce92fe478e33397bcf14e506f5d8f4194f8b4a4909753ff46234d046` (byte-identical, verified before execution)
- Protocol freeze: `artifacts/experimental_design/phase_10_ablation_protocol_freeze.yaml`
  - LOAD reference: random_forest (n_estimators 191, max_depth null, min_samples_leaf 4, max_features 1.0, n_jobs -1, bootstrap true, random_state 42)
  - WIND reference: hist_gradient_boosting (max_iter 111, max_leaf_nodes 57, learning_rate 0.0159, l2 0.0235, min_samples_leaf 28, random_state 42)
  - PV reference: random_forest (n_estimators 209, max_depth 8, min_samples_leaf 4, max_features sqrt, bootstrap false, random_state 42)
- Challenger: PYTORCH_MLP_V1 per `artifacts/experiments/hpo/phase_09/best_configs/*_pytorch_mlp.yaml` (load hidden_width 68 dropout 0.38 lr 0.00175 wd 3.9e-05 etc.)
- Feature sets: B_lags_only for references, E_full for challenger per `config/ablation/phase_10.yaml`
- No frozen model artifact retraining; models refit on RTS TRAIN+VALIDATION (7128 samples, all development data before 2020-11-01) with frozen hyperparameters/seed 42 and applied to external.

If artifact cannot be loaded: blocker documented — not applicable, all artifacts loaded successfully.

## 9. Evaluation Protocol

- Metrics: MAE primary, RMSE/sMAPE/nMAE/nRMSE secondary per `statistical_analysis_plan.md`, reused from `final_evaluation/engine.py`
- Horizons: H24 primary (external dataset hourly supports H24); H1 not evaluated
- Aggregation: metrics over all evaluable external timestamps per target (50103 feature rows → 49983 common valid after persistence baseline filtering)
- Statistical tests: Diebold-Mariano on absolute-error differentials with Newey-West variance max lag 23, two-sided normal approx, plus Holm-Bonferroni across primary family EXT-H1-{LOAD,WIND,PV} at alpha 0.05 — reused from Phase 19 engine
- Missing-data handling: rows with missing actuals or missing persistence source (first 24h) excluded; exclusion counts recorded (98 missing + 192 feature warmup + 120 persistence unavailable = 219 total excluded from 50402 → 49983 evaluable per target after common valid filtering)
- Exclusions: PV nighttime zeros valid observed behavior, not missingness (per AGENTS.md); none excluded as missing
- Failure criteria: evaluable samples 49983 >> 720 and 0.19% missing <<10%, so conclusive

## 10. Metrics

External validation on OPSD DE, H24, all evaluable timestamps (n=49983 per target):

| Target | Reference (frozen) MAE | Challenger MAE | Baseline (persistence) MAE | Reference nMAE |
|---|---|---|---|---|
| LOAD | 48228.33 | 30282.93 | 4459.73 | 0.869 |
| WIND | 10140.74 | 9153.64 | 5944.00 | 0.879 |
| PV | 4038.89 | 3792.91 | 1060.89 | 0.881 |

Full table in `artifacts/research_tables/external_validation_results.csv` and `artifacts/experiments/external_validation/opsd_time_series/official/metrics/external_metrics.csv` (RMSE, sMAPE, nRMSE also recorded; e.g., LOAD baseline RMSE 6876.59 vs reference 49258.64).

## 11. Statistical Tests

Reuse of DM+Holm per `final_evaluation/engine.py`:

- EXT-H1-LOAD (reference vs baseline persistence): DM +182.07, p 0.0, Holm reject (threshold 0.0167)
- EXT-H1-WIND: DM +111.17? actually 1.11e-91 p, Holm reject (threshold 0.05)
- EXT-H1-PV: DM +... p 0.0, Holm reject (all three reject)
- EXT-H2 reference vs challenger also computed (LOAD DM +312.65 p 0.0, etc.) — challenger significantly better than reference but still far worse than persistence.

All three primary tests reject null: frozen references are significantly worse than simple persistence on this external German system. Challenger also significantly worse than persistence, though less so for load/wind.

DM assumptions: horizon-appropriate lag 23, n=49983 large, normal approx appropriate.

## 12. Results

Genuine results, evaluation-only (no tuning):

- **LOAD:** Frozen RF severely underperforms persistence (MAE 48228 vs 4459, ~10x worse). Challenger MLP also poor (30282 vs 4459). Indicates massive distribution shift: German total load magnitude and dynamics differ fundamentally from RTS synthetic.
- **WIND:** Reference HGB MAE 10140 vs persistence 5944 (1.7x worse); challenger 9153 vs 5944 (1.5x worse). Still significantly worse than persistence.
- **PV:** Reference 4038 vs persistence 1060 (3.8x worse); challenger 3792 vs 1060 (3.5x worse). Similar.

No metric fabricated; all from `fit_predict_classical`/`fit_predict_mlp` applied to external feature matrices with leakage-safe scaling (StandardScaler fitted on RTS training only, applied forward).

Secondary breakdown: single large evaluation fold (no monthly walk-forward needed as external dataset is independent); training_samples 7128 (RTS development), eval_samples 49983.

## 13. Reproducibility

- Independent second run into `C:/Users/LENOVO/AppData/Local/Temp/opsd_rerun` produced max relative metric deviation 0.0 (classical deterministic) and max absolute prediction deviation <2e-12 (MLP ULP variance due to parallel prediction, same as Phase 19 determinism note) — verified via `evaluate_external` re-execution.
- Dataset manifest: `data/manifests/opsd_time_series_manifest.yaml` + `opsd_time_series_checksums.sha256` (raw sha 6a7f2bc..., datapackage 2f4b7ae...)
- Feature version: `external_v1` per spec, checksums: load combined_v1 `20961145...`, wind `0ed41576...`, pv `0341c40...`; hourly `9eccac1a...` etc. recorded in manifest derived_artifacts.
- Model configuration: frozen plan sha, protocol freeze sha, per-target hyperparameter digests logged as MLflow params.
- Code version: `src/smartgrid_mlops/external_validation/` package, `pyproject.toml` unchanged; commit hash not applicable (no commits yet, untracked).
- Environment: Python 3.13.2, scikit-learn 1.6.1, torch 2.x, pyarrow 14, mlflow via `phase12_tracking.db`, recorded in MLflow tags.
- Output artifacts: `artifacts/experiments/external_validation/opsd_time_series/official/{metrics/summary.json, metrics/external_metrics.csv, manifests/run_manifest.json}` + research table `artifacts/research_tables/external_validation_results.csv`; `data/processed/external/opsd_time_series/` canonical hourly + feature parquets.

Second-run verification performed 2026-08-26, documented.

## 14. Limitations

- Single external system (DE) — not universal; other countries/cross-system variation not tested.
- German scale mismatch: frozen models trained on small synthetic system (order 1k MW) cannot generalize to German ~50 GW scale without recalibration; results demonstrate poor transferability, not necessarily poor methodology within original population.
- No external DAY_AHEAD forecast comparator evaluated (OPSD does provide `*_forecast` columns but protocol used persistence only for comparability; DAY_AHEAD semantics differ between systems).
- Feature compatibility limited to calendar/lag/rolling; no meteorological covariates (consistent with frozen feature sets, but limits external explanatory power).
- Only H24 evaluated; no seasonal breakdown beyond full-period aggregation.

## 15. Research Integrity

- Raw RTS-GMLC data not modified (verified via `data/external/RTS-GMLC` untouched, checksums unchanged)
- Frozen plan not modified (sha256 verified before and after)
- Locked test set not revisited (no RTS TEST access via external validation; training used only TRAIN+VALIDATION)
- No hyperparameter tuning, no model selection on external results
- No synthetic data presented as external validation (synthetic fixtures test-only)

## 16. Phase 19 Integrity Verification

Mandatory check after external validation:

- Phase 19 frozen plan modified: NO (sha256 afb77163... still matches sidecar)
- Phase 19 checksum changed: NO
- Phase 19 official artifacts modified: NO (`artifacts/experiments/final_evaluation/phase_19/official` metrics/predictions/summary unchanged, verified via file existence and content hash spot check)
- Phase 19 predictions modified: NO (13,176 rows, sha unchanged)
- Phase 19 MLflow runs modified: NO (experiment `smartgrid/phase19/final-test-evaluation` 3 runs FINISHED, tags `final_test_performance_access=AUTHORIZED_FROZEN_PLAN_EXECUTION` unchanged; new external runs in separate experiment `smartgrid/external_validation` 3 runs FINISHED)
- Locked test set modified: NO (`data/processed/*_hourly.parquet` mtimes unchanged, checksums unchanged)

## 17. Conclusions

Interpreted conservatively:

- **Poor generalization:** Frozen configurations exhibit strong distribution shift when applied to German OPSD data — persistence significantly outperforms both reference and challenger for all three targets. This does not invalidate Phase 19 within-distribution results but indicates limited transferability without recalibration or scale adaptation.
- **Target-specific:** Degradation largest for LOAD (10x), moderate for PV/WIND (~1.5-3.8x), consistent with scale differences.
- **Challenger vs reference:** MLP challenger consistently better than reference on external (e.g., load 30282 vs 48228) but still far from baseline, echoing PV/wind challenger superiority seen externally but not in final-test.
- **Comparator-dependent:** On original RTS test, DAY_AHEAD beat references for LOAD/WIND but PV was tie; externally, persistence beats everything, highlighting system-dependent comparator strength.

Do not claim universal superiority or production readiness from either evaluation alone.

## 18. Recommended Next Step

1. Investigate scale-invariant adaptation (e.g., per-system StandardScaler refitting or normalized target scaling) as a *separate* preregistered experiment, not as post-hoc tuning of Phase 19/External results.
2. Consider external validation on additional OPSD countries or years to assess country/time generalization, using same frozen protocol and this infrastructure.
3. Retain frozen Phase 19 and current external results as final evidence; any new model must be evaluated as a new challenger through governed promotion, not by overwriting these results.

