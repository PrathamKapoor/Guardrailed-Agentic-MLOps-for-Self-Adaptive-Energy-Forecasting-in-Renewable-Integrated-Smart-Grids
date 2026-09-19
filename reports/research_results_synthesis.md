# Research Results Synthesis

## 1. Research Question

Whether bounded Agentic AI can reduce manual intervention in an MLOps forecasting lifecycle without having unrestricted authority over critical model decisions, evaluated on electricity demand (LOAD), wind (WIND), and utility-scale PV generation forecasting for renewable-integrated smart grids.

## 2. Experimental Design

- **Population:** RTS-GMLC 2020 synthetic system, 8,784 hourly observations, single year. Partitions: TRAIN 2020-01-01..08-31, VALIDATION 09-01..10-31, locked TEST 11-01..12-31 (target_timestamp-driven). Rolling-origin validation: 6 expanding-window folds (May-Oct) for development; walk-forward monthly folds for final test (F11 Nov, F12 Dec).
- **Horizons:** H24 primary (comparable to RTS DAY_AHEAD), H1 secondary.
- **Metrics:** MAE primary, RMSE/sMAPE/nMAE/nRMSE secondary. Paired absolute-error Diebold-Mariano (Newey-West lag 23) + Holm-Bonferroni alpha 0.05 familywise.
- **Governance:** Deterministic policy gates authoritative; agents advisory-only with firewall (investigate/summarize/explain/request review/create report only).

## 3. Data

- **Development/final-test:** RTS-GMLC hourly canonical (research_hourly_index 8,784, usable 8,592 H24 after 192 rows lost for lag_168+horizon). Checksums: load_hourly `c65db401...`, wind `8863a0...`, pv `b36a773...`, feature combined_v1 H24 per-target checksums in `feature_manifest.yaml`.
- **External:** OPSD Time Series 2020-10-06 German DE (ENTSO-E actuals) 2015-01-01 07:00 to 2020-09-30 23:00, 50,295 valid hourly rows, 50,103 feature rows H24, 49,983 evaluable after persistence filtering. Manifest `opsd_time_series_manifest.yaml` sha `6a7f2bc...`.

## 4. Model Development

- **Feature sets:** `config/ablation/phase_10.yaml` B_lags_only (lag_1/24/168) selected for references via ablation; E_full (12 features: calendar + lags + rolling_mean_24/168 + ramp) for MLP challenger.
- **Model families:** Classical untuned (linear, ridge, RF, extra_trees, HGB) and neural MLP/LSTM/GRU (untuned), then HPO (Optuna 5 trials, 4 folds F01-F04) for MLP, ablation across 5 feature sets (F01-F04), confirmation on F05-F06, finalist selection per target: LOAD RF B_lags_only, WIND HGB B_lags_only, PV RF B_lags_only (per `final_test_comparison_plan.yaml` matrix).
- **Tuning:** Classical hyperparameters from `phase_10_ablation_protocol_freeze.yaml` (LOAD RF n_estimators 191 etc.), MLP from `phase_09/best_configs/*`. No tuning used TEST; seeds 42 (classical) + 5 MLPs mean-aggregated.

## 5. Phase 19 Final Evaluation

- **Status:** FROZEN plan executed 2026-08-26, `AccessMode.FINAL_EVALUATION` with `configuration_frozen=True`, every TEST timestamp authorized, plan sha `afb77163...` verified.
- **Training:** Refit on TRAIN+VALIDATION (7,128 samples for F11, 7,848 for F12) per frozen hyperparameters; predict Nov (720) + Dec (744) = 1,464 per target.
- **Results (n=1,464, H24):**
  | Target | Ref MAE | Baseline MAE | Challenger MAE | DM | p | Holm |
  |---|---|---|---|---|---|---|
  | LOAD RF B_lags_only vs DAY_AHEAD | 174.26 | 101.14 | 281.00 | +6.10 | 1.07e-09 | reject |
  | WIND HGB B_lags_only vs DAY_AHEAD | 778.84 | 331.30 | 838.40 | +7.98 | 1.47e-15 | reject |
  | PV RF B_lags_only vs persistence | 36.12 | 39.10 | 221.64 | -0.78 | 0.438 | retain |
- **MLflow:** `smartgrid/phase19/final-test-evaluation` 3 runs FINISHED, tags `final_test_performance_access=AUTHORIZED_FROZEN_PLAN_EXECUTION`.
- **Predictions:** `artifacts/experiments/final_evaluation/phase_19/official/predictions/final_test_predictions.parquet` 13,176 rows.

## 6. External Validation

- **Status:** Same frozen configs applied to OPSD DE (no retuning).
- **Training:** Same RTS TRAIN+VALIDATION (7,128 samples); evaluation on all OPSD evaluable rows (49,983 per target, 2015-2020).
- **Results (n=49,983, H24):**
  | Target | Ref MAE | Challenger MAE | Persistence MAE | DM ref vs pers | p | Holm |
  |---|---|---|---|---|---|---|
  | LOAD | 48,228.33 | 30,282.93 | 4,459.73 | +182.07 | 0.0 | reject |
  | WIND | 10,140.74 | 9,153.64 | 5,944.00 | +20.31 | 1.11e-91 | reject |
  | PV | 4,038.89 | 3,792.91 | 1,060.89 | +40.56 | 0.0 | reject |
- All three references significantly worse than persistence on external German scale; challenger consistently better than reference but still far from baseline.

## 7. Transferability Findings

- **Internal:** References beat or tie baselines for WIND/LOAD? Actually WIND/LOAD DAY_AHEAD beat references internally; PV tie. So internal shows limited superiority over strong external forecast baselines.
- **External:** Persistence beats everything, indicating strong distribution shift (German total load ~55 GW mean vs RTS ~1-3 GW; wind/PV scales also larger). Scale alone could explain magnitude (reference nMAE 0.87-0.88 on external vs 0.047-0.67 internal).
- **Survived:** PV tie vs persistence internally survived? Externally PV still loses, but within same order. No model survived external as superior.
- **Failed to generalize:** All three frozen lag-only references fail to transfer to German OPSD without recalibration.

## 8. Statistical Evidence

- Primary tests: DM with Newey-West (lag 23) reused from Phase 19 engine, Holm across 3 hypotheses per evaluation (internal and external separately). All internal LOAD/WIND rejections are strong (p<1e-9), PV retain; all external rejections are extreme (p 0.0 or 1e-91). No p-value hacking; secondary reference vs challenger tests are descriptive (e.g., external LOAD DM +312 p0.0).

## 9. Failure Modes

- Scale mismatch (order magnitude), geography/grid composition, weather regime, generation mix, load shape, measurement definitions. Feature distributions shifted: lag values from German series have different mean/variance than RTS training; StandardScaler fitted on RTS training applied forward preserves shift rather than correcting it (by design, to avoid leakage).
- No weather covariates limits adaptability to new climate.
- Single-year development limits interannual robustness.

## 10. What the Results Support

- That bounded agentic governance can coexist with deterministic MLOps through Phase 18 (governance, retraining, champion-challenger simulation, agentic ablation) without becoming final authority — supported by scenario tests and policy gates.
- That frozen lag-only references are not superior to strong external baselines on locked TEST (for LOAD/WIND) — supported by final-test DM.
- That the same references do not transfer to German OPSD via naive application — supported by external DM.

## 11. What the Results Do NOT Support

- Does NOT support claim of universal superiority, robustness, state-of-the-art, production-readiness, or transferability.
- Does NOT support that agentic AI improves forecasting accuracy (agentic evaluation measured operational support, not accuracy).
- Does NOT support quantum/post-quantum or five-agent Quantum Trust claims — those are foreign to classical evidence (see claim audit).
- Does NOT support that MLP challenger is generally better (internal WIND reference beat challenger? Actually internal challenger MAE 281 vs ref 174 for LOAD, worse; external challenger better than ref but still worst vs baseline).

## 12. Limitations

- Single-year, single synthetic system for development; single external country (DE) for transfer test.
- German scale mismatch not mitigated (no per-system normalization experiment run).
- No external DAY_AHEAD comparator evaluated (persistence only).
- Only H24 evaluated externally; no seasonal breakdown.
- No meteorological covariates.
- Local MLflow backend, no distributed serving.
- Single 168h lookback, limited architectures.

## 13. Research Implications

- Governance and transferability are orthogonal: lifecycle automation does not guarantee cross-system generalization.
- Scale-aware evaluation (nMAE/nRMSE) exposes shift that MAE alone obscures but does not fix it.
- Negative external result is valuable: motivates per-system calibration or normalized target modeling as next preregistered experiment, not post-hoc tuning.
- Persistence is a hard baseline to beat on external high-autocorrelation load after distribution shift.

## 14. Future Experiments

PRE-REGISTERABLE (per `docs/research_methodology/future_experiments.md` to be created):
- Scale-normalized transfer (per-system StandardScaler refitting, normalized MAE)
- Additional-country transfer (OPSD FR, AT, etc.)
- Additional-year transfer (if RTS-GMLC releases new year)
- Target-specific adaptation (e.g., separate PV handling)

POST-HOC EXPLANATION (not preregistered, must be labeled as exploratory):
- Any analysis of why German load shape differs, attribution to generation mix, etc., without new data.

