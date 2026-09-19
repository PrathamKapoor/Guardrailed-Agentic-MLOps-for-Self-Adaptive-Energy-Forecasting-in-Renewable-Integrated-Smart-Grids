# Phase 19 completion report

## Phase status

**PHASE 19 COMPLETE — final frozen evaluation and generalization assessment.**
Phase 20 was not begun. No model changes, HPO, feature selection, model selection,
governance tuning, or retraining occurred on the locked test partition.

## Authorization

The Phase 19 protocol freeze was created and SHA-256-frozen
(`79053d6faab827806f4f8d4f6b7915888e0e6ed34c736d230a3824492e5b99a5`) BEFORE
any official execution. The frozen comparison plan
`artifacts/experimental_design/final_test_comparison_plan.yaml` was verified
at run time (its plan SHA-256 matches its sidecar). All test-partition access
goes through `AccessMode.FINAL_EVALUATION` with `configuration_frozen=True`
and `authorize_final_evaluation`, which blocks any access path that is not
explicitly final-test authorized.

## Frozen protocols used

- Phase 19 protocol freeze: `artifacts/experimental_design/phase_19_final_evaluation_protocol_freeze.yaml` (NEW)
- Phase 11 finalist registry: `artifacts/model_registry/forecasting_reference_registry.yaml` (UNCHANGED)
- Phase 10 ablation protocol: `artifacts/experimental_design/phase_10_ablation_protocol_freeze.yaml` (UNCHANGED)
- Phase 9 best configs: `artifacts/experiments/hpo/phase_09/best_configs/` (UNCHANGED)
- Phase 10 selected feature freeze: `config/ablation/phase_10.yaml` (UNCHANGED)
- Phase 13 governance policy v13.0.0 (UNCHANGED)
- Phase 15 retraining policy v15.0.0 (UNCHANGED)
- Phase 16 promotion policy v16.0.0 (UNCHANGED)

All 19 prior freeze checksums (now 20 with Phase 19) are intact.

## Models evaluated (frozen)

| Target | Candidate ID                          | Model                  | Feature set | Training window |
| ---    | ---                                   | ---                    | ---         | ---              |
| load   | P10-load-random_forest-B_lags_only    | random_forest          | B_lags_only | 2020-01-01 .. 2020-10-31 |
| wind   | P10-wind-hist_gradient_boosting-B_lags_only | hist_gradient_boosting | B_lags_only | 2020-01-01 .. 2020-10-31 |
| pv     | P10-pv-random_forest-B_lags_only     | random_forest          | B_lags_only | 2020-01-01 .. 2020-10-31 |

## Dataset split

- **Final test partition**: 2020-11-01T00:00:00 to 2020-12-31T23:00:00 (1464 hourly rows per target). Excluded from every prior phase. The walk-forward folds are F11 (November) and F12 (December).
- **Walk-forward convention**: training cutoff for fold F11 is 2020-11-01 (no test timestamps leak in); for F12 it is 2020-12-01.
- **Canonical research index**: `data/processed/research_hourly_index.parquet` (8784 rows, full year 2020).
- **Per-target parquet**: `data/processed/{load,wind,pv}_hourly.parquet` (canonical targets + day-ahead where applicable).
- **Per-target features**: `data/processed/features/{target}/h24/combined_v1.parquet`.

## Metrics (per configuration, per target, 1464 rows)

| Target | Configuration        | MAE     | RMSE    | sMAPE   | nMAE    | nRMSE   |
| ---    | ---                  | ---     | ---     | ---     | ---     | ---     |
| load   | reference (RF)       | 174.257 | 231.271 |   4.717 | 0.0474  | 0.0628  |
| load   | challenger (MLP)     | 281.001 | 343.359 |   7.777 | 0.0764  | 0.0933  |
| load   | RTS_DAY_AHEAD        | 101.142 | 101.845 |   2.717 | 0.0275  | 0.0277  |
| wind   | reference (HistGB)   | 778.841 | 923.373 |  92.397 | 0.6790  | 0.8050  |
| wind   | challenger (MLP)     | 838.401 | 957.930 |  96.131 | 0.7309  | 0.8351  |
| wind   | RTS_DAY_AHEAD        | 331.302 | 491.208 |  50.916 | 0.2888  | 0.4282  |
| pv     | reference (RF)       |  36.122 |  82.079 | 117.735 | 0.1082  | 0.2458  |
| pv     | challenger (MLP)     | 221.640 | 244.103 | 135.468 | 0.6639  | 0.7310  |
| pv     | H24_DAILY_PERSISTENCE |  39.095 | 110.825 |   7.863 | 0.1171  | 0.3320  |

## Benchmark comparison (frozen model vs external)

| Target | Frozen MAE | Benchmark MAE | Δ absolute | Δ relative |
| ---    | ---        | ---           | ---        | ---        |
| load   | 174.26     | 101.14 (RTS_DAY_AHEAD)      | +73.11 |  +72.29% |
| wind   | 778.84     | 331.30 (RTS_DAY_AHEAD)      | +447.54 | +135.08% |
| pv     |  36.12     |  39.09 (H24_DAILY_PERSISTENCE) |  −2.97 |   −7.61% |

## Statistical analysis (registered only)

- Error distributions per target: `artifacts/research_figures/phase_19/final_error_distribution.png`.
- Forecast vs actual: `artifacts/research_figures/phase_19/forecast_vs_actual_plots.png`.
- Diebold-Mariano pairwise statistic and Holm-Bonferroni step-down across FT-H1-LOAD/WIND/PV: `artifacts/experiments/final_evaluation/phase_19/official/metrics/holm_bonferroni.json`.
- No new statistical tests were introduced.

## Lineage verification

Model and feature fingerprints come from the Phase 11 finalist registry and
the Phase 10 selected feature freeze. Dataset lineage: `data/processed/research_hourly_index.parquet`
(`data/manifests/processed_dataset_manifest.yaml` is the source of truth for the manifest
SHA-256 in the audit). MLflow: 3 official runs (one per target) with
`evidence_status = FINAL_EVALUATION_VALID` and
`final_test_performance_access = AUTHORIZED_FROZEN_PLAN_EXECUTION`. Registry identity:
3 REFERENCE + 18 CHALLENGER entries (Phase 13/15/16) — UNCHANGED.

## Governance verification

- Model promoted during Phase 19: **0**
- New challengers created: **0**
- Governance state changes: **0**
- Rollback events: **0**
- Phase 13 governance policy checksum: unchanged.
- Phase 15 retraining policy checksum: unchanged.
- Phase 16 promotion policy checksum: unchanged.
- All 20 protocol freeze checksums unchanged.

## Agentic verification

- Agents modified: **NO** (Phase 17 agent package unchanged).
- Allowed for final-test evaluation: REPORT_GENERATION_AGENT, EVIDENCE_RETRIEVAL_AGENT (advisory use only).
- Forbidden: agent-driven model changes (structurally impossible — agents have no model mutation entry points).

## Audit results

- `artifacts/audit/phase_19_final_execution_audit.json`: execution timestamp, protocol versions, model/feature/dataset fingerprints, final-test access record, metrics generated, artifacts created, governance invariants.
- `artifacts/experiments/final_evaluation/phase_19/official/manifests/run_manifest.json`: per-run manifest with access log and configuration hashes.

## Limitations

- Single dataset (RTS-GMLC, 2020 leap year, 8784 rows).
- Final test is a single 2-month window; generalization beyond November-December 2020 is unobserved.
- Synthetic drift and simulated operational workflows in Phases 14-18.
- No production deployment; no real operator study; agentic effort reduction approximated by a frozen cost model.
- External benchmark (RTS_DAY_AHEAD) is a strong short-horizon published forecast; the comparison is informative, not aspirational.

## Tests

- `.venv\Scripts\python.exe -m pytest`: **213 passed, 0 failed, 0 skipped, 0 warnings** (208 pre-final + 5 Phase 19 test additions via the existing `tests/test_phase19_final_evaluation.py`).
- `.venv\Scripts\python.exe -m compileall -q src scripts tests`: **PASS**
- `.venv\Scripts\python.exe scripts/bootstrap_rts_gmlc.py --verify-only`: **Integrity: PASS; Manifest: PASS; Checksums: PASS**
- All 20 freeze checksums (19 prior + Phase 19): **PASS**

## Integrity

| Artifact | SHA-256 |
| --- | --- |
| Phase 19 protocol freeze | 79053d6faab827806f4f8d4f6b7915888e0e6ed34c736d230a3824492e5b99a5 |
| Frozen comparison plan   | (recorded in audit JSON `metrics_generated` and run_manifest) |
| Phase 11 finalist registry | (UNCHANGED) |
| Phase 10 ablation protocol | (UNCHANGED) |
| Phase 13 governance policy | (UNCHANGED) |
| Phase 15 retraining policy | (UNCHANGED) |
| Phase 16 promotion policy  | (UNCHANGED) |

## Phase 20 readiness

**READY.** All Phase 0–19 evidence is finalized; the research evidence package can be assembled.
