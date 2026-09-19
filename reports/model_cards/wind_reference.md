# WIND H24 research reference card

## Purpose

Frozen internally trained reference for subsequent bounded MLOps research.

## Specification and development evidence

- Target / horizon: WIND / H24
- Model family: hist_gradient_boosting
- Feature set: B_lags_only
- Development F05–F06 MAE: 528.4055877683035
- Strongest benchmark: RTS_DAY_AHEAD (MAE 269.0056523224044)
- DEVELOPMENT_BENCHMARK_GATE: FAIL
- Model specification fingerprint: `model-spec-v1:sha256:b926cca84e5aa1e32684f7cc93fa69d516382f49a76432bbedc168f925a566ca`
- Data lineage: RTS-GMLC → `rts_gmlc_processed_v1` → H24 feature manifest
- Feature lineage: `config/ablation/phase_10.yaml` → `B_lags_only`
- Protocol: Phase 10 fixed specification and Phase 11 development-only selection
- Final-test performance: NOT_EVALUATED

## Known limitations and intended role

Single-year research-system data, no meteorological covariates, and development-only evidence limit generalization. This model is the frozen internally trained research reference for subsequent MLOps experiments. It does not currently outperform the strongest development benchmark and must not be interpreted as production-promotion eligible.
