# External Validation Methodology

## Purpose

External validation evaluates the frozen forecasting configurations selected during development on an approved dataset that was not used for any training, validation, model selection, hyperparameter optimization, feature selection, architecture selection, or threshold tuning decision. It assesses generalization independently of the locked final-test partition (2020-11-01 .. 2020-12-31) already used for Phase 19.

This document defines requirements, governance, and reproducibility for that evaluation. It does not introduce data, perform inference, or select models. Execution may occur only after a dataset satisfying these requirements is recorded in `data/manifests/` with full provenance.

Status: PROTOCOL FROZEN — NO EXTERNAL DATASET APPROVED
Classification: DOCUMENTED (Phase 19 engine verified; this protocol documented)

## Evaluation Population and External Definition

- **Current evaluation population (VERIFIED):** RTS-GMLC 2020 synthetic system, 8,784 hourly observations, single operating year, three targets (LOAD, WIND, PV), primary horizon H24, secondary H1. Temporal partitions: TRAIN 2020-01-01 .. 2020-08-31, VALIDATION 2020-09-01 .. 2020-10-31, locked TEST 2020-11-01 .. 2020-12-31. All development decisions used only TRAIN/VALIDATION or pre-test rolling-origin folds per `src/smartgrid_mlops/experimental_design/protocol.py`.
- **What constitutes external (DOCUMENTED):** Per `AGENTS.md` Dataset policy, only explicitly approved datasets may be used. Threats to validity (`docs/research_methodology/threats_to_validity.md`) lists single-year coverage, seasonal representativeness, and development-only evidence as limitations mitigated by external validation. External therefore means a dataset independent of the RTS-GMLC 2020 distribution used for Phases 01-19, recorded in `data/manifests/` before use, and not accessed during any prior model selection. A second synthetic year from the same RTS-GMLC generator would be external if temporally disjoint and independently generated; a different operational grid or research system with compatible targets is also external. Re-partitioning the existing 2020 TEST data is NOT external.
- **Another year from same system (INFERRED):** RTS-GMLC as acquired (`data/external/RTS-GMLC`, archive `/home/makan/Downloads/RTS-GMLC-master.zip` 2026-08-13) supplies only 2020. A holdout year does not exist locally. If the upstream RTS-GMLC project releases additional synthetic years, they would qualify provided they pass provenance and independence checks.
- **Second dataset anticipated (DOCUMENTED):** `docs/research_progress.md` marks External Validation NOT STARTED; `threats_to_validity.md` repeatedly cites external validation as required mitigation. No acquisition manifest for a second dataset exists in `data/manifests/` (only `rts_gmlc_manifest.yaml`, `feature_manifest.yaml`, `processed_dataset_manifest.yaml`, `rts_gmlc_checksums.sha256` present — VERIFIED).
- **Acquisition convention (VERIFIED):** `scripts/bootstrap_rts_gmlc.py` defines the approved workflow: preferred local ZIP validation, fallback `git clone https://github.com/GridMod/RTS-GMLC.git`, and manifest recording. External acquisition must follow the same convention: source, license, retrieval date, version, schema, approval recorded in `data/manifests/` before experiment use.

## Dataset Requirements

### Source characteristics

- Origin must be documented with source URL or archive path, license, retrieval date, version/commit, and approval per `AGENTS.md`.
- Provenance must be traceable: archive checksum (sha256), dataset version string, schema description, and manifest entry in `data/manifests/`.
- Licensing must explicitly permit research use; if restricted, approval must be recorded before ingestion.

### Temporal requirements

- Coverage: minimum one continuous month of hourly observations per target to support horizon H24 evaluation; ideally multiple months to permit stable estimates.
- Sampling frequency: hourly, aligned to start-of-interval timestamps as in `research_hourly_index.parquet` (one-based Period -> start-of-interval convention).
- Forecast horizons: H24 primary (comparable to RTS-GMLC DAY_AHEAD external benchmark semantics where applicable); H1 diagnostic only if external system provides equivalent granularity.
- Independence: temporal window must not overlap any period used for training/validation/test of the frozen configurations (2020-01-01 .. 2020-12-31). If sourced from the same generator, generation seed must differ and be documented.

### Targets required

- LOAD (system-level electricity demand) — REQUIRED.
- WIND (utility-scale wind generation aggregated) — REQUIRED where available; if external system has no wind, evaluation proceeds on available targets and the absence is documented.
- PV (utility-scale solar) — same as WIND.
- At minimum one of LOAD/WIND/PV must be present with hourly actuals; absence of a target does not invalidate evaluation of the others.

### Feature requirements

- Hourly actuals per target are mandatory for label construction.
- Calendar features (hour_sin/cos, dow_sin/cos, doy_sin/cos) are derivable from timestamps alone and require no external covariates.
- Lag features (lag_1, lag_24, lag_168) and rolling means require contiguous history; at least 168 hours of prior actuals must precede the first evaluable target_timestamp for B_lags_only (lag_168 dependency). Rows lacking required lags must be excluded and counted as rows_lost, consistent with `feature_manifest.yaml`.
- External forecast baselines (e.g., DAY_AHEAD) are optional comparators; if present, they must be external forecast series, not derived from actuals, and must have documented issuance semantics.

### Sampling frequency and minimum sample size

- Hourly frequency required; sub-hourly must be aggregated by arithmetic mean of 12 five-minute samples (as in `src/smartgrid_mlops/data/aggregation.py` hourly_mean) if source provides RTS-GMLC-like 5-min resolution.
- Minimum evaluable sample: 720 hourly target timestamps per target after lag/rolling exclusion (one month). Results with smaller samples are descriptive only and must not be presented as conclusive external validation.

### Provenance requirements

- `data/manifests/<dataset>_manifest.yaml` must contain: source, license, retrieval_date, version, schema (column names, types, timestamp convention), approval, archive_checksum.
- `data/manifests/<dataset>_checksums.sha256` must record file-level sha256 for every ingested raw file.
- Raw data must remain immutable under `data/external/<dataset>/`; derived canonical and feature artifacts go under `data/processed/` and `data/processed/features/<target>/h<horizon>/` with versioned naming (e.g., `<dataset>_external_v1`).

## Model Policy

External validation must use THE SAME FROZEN CONFIGURATIONS used for Phase 19 final-test evaluation.

- Reference models: per-target winners from `artifacts/experimental_design/final_test_comparison_plan.yaml` with hyperparameters from `artifacts/experimental_design/phase_10_ablation_protocol_freeze.yaml` (LOAD random_forest, WIND hist_gradient_boosting, PV random_forest) — VERIFIED frozen.
- Challenger: PYTORCH_MLP_V1 with per-target HPO best configs from `artifacts/experiments/hpo/phase_09/best_configs/*_pytorch_mlp.yaml`.
- No retuning, no new model selection, no threshold tuning based on external performance. If the frozen configuration is unavailable or corrupted, document the blocker and do not reconstruct by tuning.

## Feature Policy

- Use the same feature definitions as in `config/ablation/phase_10.yaml` wherever technically applicable (B_lags_only for references, E_full for challenger where defined).
- Scaling: StandardScaler fitted on the frozen training window only (the original RTS-GMLC TRAIN+VALIDATION for 2020 models), then applied forward to external features. Never fit scaling on external data in a way that leaks external target information into training.
- Any unavoidable mapping difference (e.g., external system has different zone aggregation for LOAD) must be explicitly documented in the external validation report, and the feature version must be recorded as distinct (e.g., `external_v1`).

## Evaluation Policy

- Metrics: MAE primary; RMSE, sMAPE, nMAE, nRMSE secondary (as in `docs/research_methodology/experimental_design.md` and `statistical_analysis_plan.md`).
- Horizons: H24 primary; H1 only if external data supports it and is explicitly declared.
- Aggregation: metrics computed over all evaluable external timestamps per target; fold-wise breakdown if external dataset spans multiple months.
- Statistical tests: Diebold-Mariano on absolute-error differentials with Newey-West variance (max lag = h-1 = 23 for H24) and Holm-Bonferroni across the primary family FT-H1-{LOAD,WIND,PV} if comparators are available, reusing `src/smartgrid_mlops/final_evaluation/engine.py`. If comparator is absent or sample too small, document why DM is inapplicable and present descriptive metrics only. Do not invent tests.
- Missing-data handling: rows with missing actuals, missing required lags, or missing comparator forecasts are excluded; exclusion counts and reasons recorded in the manifest.
- Exclusions: nighttime PV zero generation is valid observed behavior, not missingness, per `AGENTS.md`.
- Failure criteria: if evaluable sample < 720 per target or more than 10% of expected hourly timestamps are missing after provenance checks, external validation for that target is descriptive only and must not be presented as conclusive.

## Governance

- External validation is evaluation-only. No promotion, deployment, rollback, or retraining may be triggered by external results.
- Deterministic policy gates remain authoritative; agent recommendations remain advisory (`AGENTS.md` Agent authority).
- No LLM/agent may bypass the governance policy engine or obtain final authority over model decisions.
- Results must be recorded with evidence status distinct from final-test evaluation (e.g., EXTERNAL_VALIDATION_VALID vs FINAL_EVALUATION_VALID) and must not overwrite Phase 19 artifacts.

## Reproducibility

- Dataset manifest: `data/manifests/<dataset>_manifest.yaml` and checksums as above.
- Feature version: `v1` or `external_v1` with checksum in `feature_manifest.yaml` or dedicated external feature manifest.
- Model configuration: frozen plan sha256, protocol freeze sha256, and per-target hyperparameter digests.
- Code version: commit hash, `pyproject.toml` / `requirements` versions, and `artifacts/experiments/external_validation/<run>/manifests/run_manifest.json`.
- Environment: Python, library versions (pyarrow, scikit-learn, torch, mlflow) recorded.
- Output artifact structure: `artifacts/experiments/external_validation/<dataset>_<version>/` with `predictions/`, `metrics/`, `manifests/` subdirectories; `artifacts/research_tables/external_validation_<dataset>.csv` for synthesis. Every result must identify dataset, target, horizon, model, comparator, feature version, evaluation configuration, provenance, and timestamp.

## Acquisition Workflow

1. Identify candidate external source that meets temporal/target/feature requirements above.
2. Obtain approval per `AGENTS.md` Workspace boundary.
3. Acquire via `scripts/bootstrap_rts_gmlc.py`-style workflow or a new `scripts/bootstrap_external_validation.py` that validates structure, computes checksums, and writes the manifest — without silent substitution.
4. Record manifest before any experiment use.
5. Build canonical and feature artifacts deterministically, storing under versioned paths and recording checksums.
6. Run `src/smartgrid_mlops/external_validation/engine.py` (to be implemented) in evaluation-only mode with frozen configurations.

Until step 2 completes, no external data may be introduced and no external validation results may be presented.

## Current Status

- No external dataset is approved or present in this repository beyond RTS-GMLC 2020 (VERIFIED via `data/external`, `data/manifests`, `data/processed` inventory 2026-08-26).
- This protocol document satisfies the acquisition specification requirement. Execution is blocked pending dataset approval per Blockers section of the final report.

## References

- `AGENTS.md` Dataset policy, Data leakage policy, Forecasting policy, Reproducibility
- `docs/research_methodology/experimental_design.md`, `statistical_analysis_plan.md`, `final_test_evaluation.md`, `threats_to_validity.md`
- `src/smartgrid_mlops/experimental_design/protocol.py` (AccessMode.FINAL_EVALUATION, authorize_partition)
- `src/smartgrid_mlops/final_evaluation/engine.py` (Diebold-Mariano, Holm-Bonferroni, test fold construction)
- `data/manifests/` existing manifests
