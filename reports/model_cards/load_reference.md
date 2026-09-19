# LOAD H24 research reference card

## Purpose

Frozen internally trained reference for subsequent bounded MLOps research.

## Specification and development evidence

- Target / horizon: LOAD / H24
- Model family: random_forest
- Feature set: B_lags_only
- Development F05–F06 MAE: 285.1046521054128
- Strongest benchmark: RTS_DAY_AHEAD (MAE 126.61306197357128)
- DEVELOPMENT_BENCHMARK_GATE: FAIL
- Model specification fingerprint: `model-spec-v1:sha256:60adb40d4904062690a9fdcec46a0b2e6e4e93a63a9383cc53f52bdb6e896122`
- Data lineage: RTS-GMLC → `rts_gmlc_processed_v1` → H24 feature manifest
- Feature lineage: `config/ablation/phase_10.yaml` → `B_lags_only`
- Protocol: Phase 10 fixed specification and Phase 11 development-only selection
- Final-test performance: NOT_EVALUATED

## Known limitations and intended role

Single-year research-system data, no meteorological covariates, and development-only evidence limit generalization. This model is the frozen internally trained research reference for subsequent MLOps experiments. It does not currently outperform the strongest development benchmark and must not be interpreted as production-promotion eligible.
