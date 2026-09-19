# PV H24 research reference card

## Purpose

Frozen internally trained reference for subsequent bounded MLOps research.

## Specification and development evidence

- Target / horizon: PV / H24
- Model family: random_forest
- Feature set: B_lags_only
- Development F05–F06 MAE: 44.17532550549145
- Strongest benchmark: H24_DAILY_PERSISTENCE (MAE 33.765095628415295)
- DEVELOPMENT_BENCHMARK_GATE: FAIL
- Model specification fingerprint: `model-spec-v1:sha256:fa10f71d878392faf48e842f652188f7f275136f141874bef283f21275d2de4a`
- Data lineage: RTS-GMLC → `rts_gmlc_processed_v1` → H24 feature manifest
- Feature lineage: `config/ablation/phase_10.yaml` → `B_lags_only`
- Protocol: Phase 10 fixed specification and Phase 11 development-only selection
- Final-test performance: NOT_EVALUATED

## Known limitations and intended role

Single-year research-system data, no meteorological covariates, and development-only evidence limit generalization. This model is the frozen internally trained research reference for subsequent MLOps experiments. It does not currently outperform the strongest development benchmark and must not be interpreted as production-promotion eligible.
