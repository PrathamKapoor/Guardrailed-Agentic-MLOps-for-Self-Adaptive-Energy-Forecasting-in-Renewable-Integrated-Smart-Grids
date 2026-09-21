# Final evaluation lineage report (Phase 19)

**Generated:** 2026-08-26T07:54:05.665944
**Status:** final_test_evaluation_complete
**Authorization:** AccessMode.FINAL_EVALUATION with configuration_frozen=True

## Model fingerprints (frozen finalist registry)

| Target | Candidate ID | Model | Feature set | MAE (dev) |
| --- | --- | --- | --- | --- |
| load | P10-load-random_forest-B_lags_only | random_forest | B_lags_only | 285.1047 |
| wind | P10-wind-hist_gradient_boosting-B_lags_only | hist_gradient_boosting | B_lags_only | 528.4056 |
| pv | P10-pv-random_forest-B_lags_only | random_forest | B_lags_only | 44.1753 |

## Feature fingerprint (Phase 10 freeze)

- B_lags_only = `['lag_1', 'lag_24', 'lag_168']` (frozen in `config/ablation/phase_10.yaml`, referenced by `phase_10_ablation_protocol_freeze.yaml`).
- Feature specification fingerprint: source-of-truth in Phase 10 freeze; derived per-target fingerprints match the phase 12 registry.

## Dataset lineage

- Canonical research index: `data/processed/research_hourly_index.parquet` (sha256 = `d788c78db0f8abcf3238984a5ce46f40042aa7f106db672eb1fe8bbcfc3d5b00`).
- Per-target parquet: `data/processed/{load,wind,pv}_hourly.parquet` (single-source datasets for forecasting).
- Per-target features: `data/processed/features/{target}/h24/combined_v1.parquet`.
- Final-test partition: 2020-11-01 .. 2020-12-31 (1464 hourly rows per target). Final-test rows were EXCLUDED from all phases 0..18; access is the FIRST and ONLY authorization.

## MLflow lineage

- MLflow runs were logged with `evidence_status = FINAL_EVALUATION_VALID` and `final_test_performance_access = AUTHORIZED_FROZEN_PLAN_EXECUTION`. Runs reference the dataset manifest sha256, the frozen-plan sha256, and the reference/challenger/baseline configuration IDs.

## Registry identity (governance invariants preserved)

- Model promoted during Phase 19: 0
- New challengers created: 0
- Governance state changes: 0
- Rollback events: 0
- Phase 13 governance policy checksum: `ee13cb365f43aefa154bff3092f22de938eb3d61cd94ec0f5c6fc521ef72c862` (UNCHANGED)
- Lifecycle registry entries: 16 (UNCHANGED)

## Previous freeze checksums (unchanged)

- Protocol freezes (Phase 7..18) all valid (verified by the pre-final validation script).
- Phase 19 protocol freeze sha256: `79053d6faab827806f4f8d4f6b7915888e0e6ed34c736d230a3824492e5b99a5` (frozen BEFORE official execution; recorded above in the audit JSON).
- Frozen comparison plan sha256: `afb77163ce92fe478e33397bcf14e506f5d8f4194f8b4a4909753ff46234d046`.

## Lineage graph

- Index: `artifacts/mlops/lineage/lineage_index.yaml` (existed since Phase 12; Phase 19 records evidence nodes for the new official run manifest under the same index).
