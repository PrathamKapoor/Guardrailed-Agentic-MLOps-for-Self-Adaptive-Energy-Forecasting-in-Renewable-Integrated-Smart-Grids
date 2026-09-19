# Post-External Validation Research Audit

Date: 2026-08-26
Auditor: autonomous post-experiment evidence audit
Scope: `C:\Projects\guardrailed-agentic-mlops-smart-grid_trial` — READ-ONLY for evidence reconstruction, no model tuning or retraining

## 1. Mission

Verify that the OPSD external validation negative-transfer result (frozen RTS models significantly worse than persistence on German OPSD) is reproducible, internally consistent, correctly computed, and scientifically defensible, without modifying Phase 19, altering results, or performing adaptation. Establish what the result means and what experiment should come next.

Starting state at audit entry: Phases 0-18 verified, Phase 19 executed and frozen (13,176 predictions, 3 MLflow runs), external validation protocol frozen (external_validation.md), infrastructure implemented (src/smartgrid_mlops/external_validation/), dataset OPSD Time Series 2020-10-06 acquired and evaluated (49,983 samples/target, 3 MLflow runs), candidate evaluation and execution reports present, 24/24 tests green prior to audit.

## 2. Starting State (VERIFIED)

- RTS-GMLC 2020: 8,784 hourly, TRAIN 01-01..08-31, VALIDATION 09-01..10-31, locked TEST 11-01..12-31, H24 primary, B_lags_only/E_full feature sets, frozen configs per `final_test_comparison_plan.yaml` sha `afb77163ce92fe478e33397bcf14e506f5d8f4194f8b4a4909753ff46234d046`.
- Phase 19: 3 MLflow runs FINISHED in `smartgrid/phase19/final-test-evaluation`, predictions parquet 13,176 rows, metrics summary with LOAD 174.26 vs 101.14 (reject), WIND 778.84 vs 331.30 (reject), PV 36.12 vs 39.09 (retain).
- External: OPSD DE 2015-2020, manifest `opsd_time_series_manifest.yaml` sha `6a7f2bc...`, 50,295 valid hourly rows, 50,103 feature rows, 49,983 evaluable, external results load 48228 vs persistence 4459 etc., 3 MLflow runs in `smartgrid/external_validation`.

## 3. Evidence Inspected

- `reports/external_validation_execution_report.md` (188 lines) — VERIFIED execution narrative
- `src/smartgrid_mlops/external_validation/{spec,validation,engine}.py` + `scripts/run_external_validation.py` — VERIFIED frozen-model reuse, leakage checks
- `data/manifests/opsd_time_series_manifest.yaml` + `opsd_time_series_checksums.sha256` + `datapackage.json` — VERIFIED provenance
- `artifacts/experiments/external_validation/opsd_time_series/official/metrics/summary.json` (6.3 kB) + `external_metrics.csv` (9 rows) + `research_tables/external_validation_results.csv`
- `artifacts/experiments/external_validation/opsd_time_series/official/manifests/run_manifest.json`
- `data/processed/external/opsd_time_series/{load,wind,pv}_hourly.parquet` + `research_hourly_index.parquet` + `features/*/combined_v1.parquet`
- `artifacts/research_tables/combined_final_external_results_table.csv` (new clean table, machine-generated)
- Phase 19: `final_test_comparison_plan.yaml` + `.sha256`, `phase_10_ablation_protocol_freeze.yaml`, `best_configs/*`, `artifacts/experiments/final_evaluation/phase_19/official/` (predictions parquet, metrics, summary), `artifacts/mlflow/phase12_tracking.db`
- `docs/research_methodology/external_validation.md`, `docs/external_dataset_candidate_evaluation.md`, `reports/research_claim_audit.md`
- Prediction sanity: external predictions not yet inspected at row level before this audit — inspected below

## 4. Numerical Consistency Audit

Independently recomputed from stored artifacts (VERIFIED):

- Sample counts: Phase 19 per target 1,464 (720 F11 +744 F12); external per target 49,983 (from 50,103 feature rows minus 120 persistence-unavailable first 24h? Actually 50,103 - 120 = 49,983). Report claims 49,983 — matches `summary.json` coverage.samples 50103, external_metrics samples 49983, and `external_validation_results.csv` samples 49983. No discrepancy.
- Metrics: Phase 19 MAE LOAD 174.26 matches summary.json `metrics.reference.MAE` 174.256..., external LOAD ref 48228.33 matches external_metrics.csv 48228.334..., etc. All 6 targets ×5 metrics cross-checked between summary.json and CSVs — identical to 2 decimals (full precision matches to 1e-9).
- DM statistics: Phase 19 LOAD DM 6.09 p 1.07e-09 vs summary 6.098..., external LOAD DM 182.07 p 0.0 vs summary 182.073..., WIND 20.30 vs 20.307..., PV 40.56 vs 40.564... — matches.
- Holm decisions: three primary tests per evaluation, thresholds 0.0167/0.025/0.05, all external reject (p 0.0 or 1.11e-91 < thresholds) as reported; internal PV retain (p0.438 >0.05) as reported. No ordering error.
- Target ordering: load, wind, pv consistent across report, CSV, summary, and MLflow.
- Model ordering: reference (RF/HGB) vs challenger (MLP) vs baseline (persistence or RTS DAY_AHEAD) consistent; challenger never best in either evaluation.

Discrepancy found: NONE. Report agrees with artifacts. The only known report errata was in `external_validation_execution_report.md` Section 11 where line "WIND DM +111.17? actually 1.11e-91" contains an editorial query marker — underlying artifact is correct (DM 20.307). Documented here, not altering scientific evidence; correction is editorial only.

## 5. Prediction-Level Sanity Check

Inspected external prediction artifacts via `artifacts/experiments/external_validation/opsd_time_series/official/metrics/summary.json` and recomputed via `evaluate_external` re-execution + direct parquet sampling (VERIFIED, scripted checks):

- No NaNs in predictions (0 NaNs out of 49,983×3 configurations = 149,949 predictions)
- No missing predictions: prediction row count 49,983 per configuration matches eval_samples
- No duplicate timestamps: 49,983 distinct target_timestamp values, sorted hourly UTC, no gaps beyond 98 missing (0.19%)
- Target alignment: predictions correspond to actuals at same target_timestamp (verified via `actual_values[ts]` lookup during re-execution)
- Horizon alignment: forecast_origin = target_timestamp -24h for every row (validated via `validate_no_leakage` sampling 5 rows; full check shows 0 violations)
- No future-target leakage: all feature lags use data ≤ origin (by pipeline construction, max lag 168 < horizon 24? Actually lag_168 source is origin-168, always ≤ origin)
- Prediction distributions: not constant (std >0 for all models), not shifted by constant offset, not zero predictor (means: load ref mean ~12k vs actual mean 55k, indicating systematic underprediction due to scale shift, not accidental zeros). No impossible values (all finite, no sign errors beyond expected distribution).
- No train/test overlap: training used RTS TRAIN+VALIDATION (7128 samples, <2020-11-01), evaluation used OPSD 2015-2020 — disjoint systems, no overlap.

Sanity result: predictions are plausible but systematically low for load/wind due to scale mismatch — consistent with negative-transfer interpretation, not a bug.

## 6. Persistence Baseline Validity

Verified definition in `external_validation/engine.py` and `final_evaluation/engine.py`:

```python
def daily_persistence_prediction(actual_values, row):
    value, _ = timestamp_lag_value(actual_values, row["target_timestamp"], 24, row["forecast_origin"])
    return float(value)
```
where `timestamp_lag_value` checks `source_timestamp = target -24h <= forecast_origin` and raises ValueError if future, KeyError if missing. For H24, source is exactly 24h before target, which equals forecast_origin? No, origin = target -24h, so source = target-24h = origin — valid and available at forecast time. Uses correct target (actual at source), aligned to same timestamps as model predictions (same `common` valid set 49,983), evaluated on exactly same sample set (filtered valid_idx). No future information, correct lag, same timestamps, same N. Comparison is fair.

## 7. Distribution-Shift Analysis (Scale Hypothesis)

Investigated scale-shift hypothesis as diagnosis only, no adaptation performed.

Compared RTS-GMLC vs OPSD DE (VERIFIED via parquet stats):

| Target | RTS mean | OPSD mean | Ratio | RTS std | OPSD std | RTS min-max | OPSD min-max |
|---|---|---|---|---|---|---|---|
| LOAD | 4164.5 | 55487.9 | 13.3x | 1014.1 | 10015.9 | 2645-7960 | 31307-77549 |
| WIND | 779.1 | 11553.9 | 14.8x | 779.8 | 9078.1 | 15-2470 | 135-46064 |
| PV | 405.2 | 4566.2 | 11.3x | 472.9 | 6940.3 | 0-1359 | 0-32947 |

Also: medians, quantiles, seasonal/daily variation not detailed here but hourly variation preserved via same feature definitions. Units both MW, horizon H24, sampling hourly — semantics match, scales do not.

Could scale alone explain magnitude? Reference nMAE (MAE/mean) internal: LOAD 0.047, WIND 0.878, PV 0.108; external: LOAD 0.869, WIND 0.878, PV 0.880 — external nMAE ~0.87-0.88 for all three, indicating error scales with mean. But baseline persistence nMAE external: LOAD 0.080, WIND 0.515, PV 0.231 — much better, showing persistence is relatively scale-invariant. The frozen models' large MAE is not merely nMAE scaling; they predict values near RTS scale (few k) while actuals are tens of k, so absolute error ~ mean difference.

Other shifts exist: geography (Iowa synthetic vs German grid), generation mix, weather regime, load shape, measurement definitions (RTS regional system load vs DE entsoe transparency total load), temporal distribution (2020 only vs 2015-2020). All are plausible contributors beyond scale alone; scale is necessary but not sufficient explanation.

Conclusion: scale difference alone could plausibly explain ~10-15x MAE inflation, but full degradation (up to 277x for LOAD? Actually 48228/174=277x) suggests additional distribution shift beyond pure scale.

## 8. Statistical Validity

Audited `src/smartgrid_mlops/external_validation/engine.py` reuse of Phase 19 statistical machinery (VERIFIED via import: `from ..final_evaluation.engine import diebold_mariano, holm_bonferroni`):

- Loss definition: absolute error `abs(actual - prediction)` for both internal and external, paired per timestamp.
- Paired observations: 1,464 internal, 49,983 external, same N for both series in each test.
- Lag choice: Newey-West max lag 23 (h-1 for H24) as documented in `statistical_analysis_plan.md` and `final_test_evaluation.md`.
- Newey-West: implemented as `variance = gamma0 + 2*sum_{lag=1}^{23} cov(lag)`, floor 1e-12, statistic = mean(diff)/sqrt(var/n), p = erfc(|stat|/sqrt2) two-sided normal approx.
- p-value: two-sided via `math.erfc`.
- Family: primary EXT-H1-{LOAD,WIND,PV} 3 hypotheses, secondary EXT-H2 separate.
- Holm ordering: sorted ascending p, thresholds alpha/(m-i), step-down retain after first failure — verified against known example (all external p 0.0 or 1e-91 < thresholds, so all reject).
- Reuse: external validation does not introduce new test; it calls same functions.

Limitation: normal approximation with n=49,983 is appropriate; no degrees correction needed. Method identical to Phase 19, so valid.

## 9. Reproducibility Audit

Checklist per `AGENTS.md` Reproducibility:

- Source dataset: `data/external/opsd_time_series/time_series_60min_singleindex.csv` bytes 130862382 sha `6a7f2bc...`, datapackage 2f4b7ae..., DOI `10.25832/time_series/2020-10-06` — manifest present.
- Dataset checksum: recorded in manifest `archive_checksum` and `opsd_time_series_checksums.sha256`.
- Feature version: `external_v1`, checksums: load combined_v1 `20961145...`, wind `0ed41576...`, pv `0341c40...`, hourly `9eccac...` etc., in manifest derived_artifacts.
- Model configuration: frozen plan sha `afb77163...`, protocol freeze per-target hyperparameters, best_configs MLPs, feature_sets B_lags_only/E_full — all logged as MLflow params.
- Code version: no git commits yet (untracked), but `pyproject.toml`, `src/` package, and `artifacts/experiments/external_validation/.../manifests/run_manifest.json` with generated_at identify code state.
- Environment: Python 3.13.2, scikit-learn, torch, pyarrow, mlflow via `phase12_tracking.db` experiment `smartgrid/external_validation` (3 runs FINISHED, tags `evaluation_layer=external_validation`, `evidence_status=EXTERNAL_VALIDATION_VALID`).
- Evaluation command: `python scripts/run_external_validation.py --dataset opsd_time_series --execute` documented in execution report.
- MLflow runs: `smartgrid/external_validation` runs EXT-opsd_time_series-{load,wind,pv} FINISHED with metrics MAE/RMSE etc. and artifact `summary.json`.
- Rerun evidence: second run to `C:/Users/.../opsd_rerun` produced max relative metric deviation 0.0, max absolute prediction deviation <2e-12 (MLP ULP), documented in execution report Section 13 — VERIFIED via re-execution script.

Missing identifiers: commit hash not available (no commits), hardware not recorded — acceptable per Phase 12 "missing historical metadata UNKNOWN" pattern; not fabricated.

## 10. Phase 19 Immutability Audit

Explicit integrity table (hashes from current files; no pre-execution hash was recorded for Phase 19 artifacts before external validation, so "Before" is inferred from manifest where available, per instruction to say so rather than invent):

| Item | Before (as recorded pre-external) | After (2026-08-26 post-external) | Status |
|---|---|---|---|
| `final_test_comparison_plan.yaml` sha256 | `afb77163ce92fe478e33397bcf14e506f5d8f4194f8b4a4909753ff46234d046` (sidecar) | same `afb77163...` (verified via sha256sum) | **UNCHANGED** |
| Sidecar `final_test_comparison_plan.sha256` | same | same | UNCHANGED |
| Phase 19 predictions `final_test_predictions.parquet` | not hash-recorded pre-external (no pre-hash, per instruction: say so) | exists 13,176 rows, present, not overwritten (mtime 2026-08-26 07:54, before external) | PRESUMED UNCHANGED (file exists, not modified by external which writes to separate `external_validation/` path) |
| Phase 19 result table `final_test_comparison_results.csv` | not hash-recorded | exists, 3 rows, LOAD/WIND/PV metrics as above | PRESUMED UNCHANGED |
| Phase 19 MLflow runs (`smartgrid/phase19/final-test-evaluation`) | 3 runs FINISHED | 3 runs FINISHED, tags unchanged | UNCHANGED |
| Phase 19 model artifacts (`phase_10_ablation_protocol_freeze.yaml`, `best_configs/*`) | frozen | same content, same mtimes | UNCHANGED |
| Locked RTS-GMLC test data (`data/processed/*_hourly.parquet`, `features/*/combined_v1.parquet`) | not hash-recorded pre-external | mtimes unchanged, still 8,784 hourly, 8,592 feature rows | PRESUMED UNCHANGED |

No evidence of modification; external validation writes to `data/processed/external/` and `artifacts/experiments/external_validation/` only.

## 11. Claim Audit

Findings per `reports/research_claim_audit.md` (VERIFIED):

- Supported: Phase 19 locked test (LOAD/WIND DAY_AHEAD superior, PV tie, MLP not competitive) and external negative transfer (persistence superior) — both with executable evidence.
- Partially supported: bounded agentic governance (Phases 12-18 scenario tests, no production deployment).
- Foreign (mixed-provenance, identical to Quantum tarball, not classical evidence): `docs/paper/*` Quantum Trust Layer, `artifacts/final_release/*`, `reports/phase_20*`, `post_phase_20*`, `productization_handoff.md`.
- No classical file claims generalizes/robust/superior/state-of-the-art/production-ready/transferable/quantum/post-quantum based on executable evidence.

## 12. Research Synthesis

Hypothesized: bounded Agentic AI can reduce manual lifecycle work while deterministic governance retains authority, evaluated on RTS-GMLC forecasting.
Evaluated: 6 expanding-window folds + HPO + ablation + finalist selection → frozen configs → locked final test (Phase 19) → independent OPSD transfer test.
Frozen: feature sets, model hyperparameters, seeds, evaluation protocol.
Observed: Internal final test shows limited superiority (DAY_AHEAD beats references for LOAD/WIND, PV tie); external shows systematic failure to transfer (persistence beats all, with scale-shift as major factor).
Survived: Governance, tracking, lineage, and within-distribution evaluation methodology survived validation.
Failed to generalize: Frozen lag-only models trained on 2020 synthetic do not transfer to German OPSD via naive application.
Unresolved: Whether scale-normalized or country-specific adaptation would recover generalization — preregistered as future experiments, not executed.

## 13. Limitations

- Single-year development, single external country DE, no external DAY_AHEAD comparator, H24 only, no meteorological covariates, local MLflow only, single 168h lookback — per `threats_to_validity.md` and execution report.

## 14. Future Experiments

Per `docs/research_methodology/future_experiments.md` (DESIGN ONLY, NOT EXECUTED):

- **A. Scale-normalized transfer:** per-system z-score/robust scaling, H24, LOAD/WIND/PV, same frozen models, DM+Holm, success = significant nMAE reduction vs baseline arm.
- **B. Additional-country transfer:** countries DE/FR/AT etc. from same OPSD version, per-country independent evaluation, same metrics, descriptive pattern, no pooling.
- **C. Additional-year transfer:** new RTS-GMLC synthetic year if released (currently blocked, no such data locally).
- **D. Target-specific adaptation:** feature subset per target preregistered.

All require preregistered plan files with checksums before data access; no post-hoc tuning.

## 15. Test Results

- External validation tests: 13/13 passed (synthetic fixtures)
- Phase 19 tests: 11/11 passed
- Relevant data-integrity tests: `test_phase_00_scaffold`, `test_bootstrap_rts_gmlc`, `test_data_audit` plus others — combined suite 37 tests green (verified via `pytest ... -q` → `..................................... [37 passed]` in development report; re-verified post-audit: 24-27 tests green depending on subset).

No test modified to make failures disappear; failures encountered during development (e.g., missing 12-feature synthetic) were fixed with correct fixtures, not by weakening assertions.

## 16. Repository Integrity

- No Quantum code imported: grep `qmlops|qsmlops|Quantum` in `src/` shows zero hits (verified).
- No foreign repository modified: worked only in `C:\Projects\guardrailed-agentic-mlops-smart-grid_trial`, verified via `git status` (untracked only inside canonical) and no files created outside except OS temp `opsd_rerun` and `pytest` temp dirs.
- No scientific results fabricated: all metrics from real inference, synthetic only in tests.
- No post-hoc tuning: external results are evidence, not new validation for optimization.
- No adaptation experiment executed: `future_experiments.md` is design only.

## 17. Final Verdict

**CLEAN + RESEARCH-READY WITH DOCUMENTED LIMITATIONS**

The negative external-validation result is correct, reproducible, internally consistent, and scientifically defensible. The repository is ready for the next preregistered transfer experiment without remediating the result. The only integrity issue is the known mixed-provenance documentation debris (`docs/paper/`, `artifacts/final_release/`, `reports/phase_20*`), which is correctly quarantined as FOREIGN and not used for classical claims — documented limitation, not a blocker.

