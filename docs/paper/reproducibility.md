**Environment**:
- Operating System: Windows (development and execution environment)
- Python: see requirements.txt for pinned dependencies (scikit-learn, pyarrow, mlflow, fastapi, uvicorn, etc.)
- Execution: final evaluation entry point at the repository root (run_final_evaluation.py); phase pipelines under scripts/ with recorded commands in each phase completion report.

**Dataset**:
- Source: RTS-GMLC (Reliability Test System - Grid Modernization Lab Consortium), National Renewable Energy Laboratory. Acquired by ZIP download on 2026-08-13; archive checksum recorded in data/manifests/rts_gmlc_manifest.yaml.
- Processing: six source time-series files (day-ahead/real-time x load/wind/PV) ingested with per-file SHA-256 checksums recorded before and after processing (source_unchanged: true in data/manifests/processed_dataset_manifest.yaml, dataset_version rts_gmlc_processed_v1).
- Coverage: 8,784 matched hourly observations per target for calendar year 2020; zero missing values; PV nighttime zeros (46.4%) retained as observed behavior.
- Final-test partition: November 1 to December 31, 2020 (1,464 hours), sealed by artifacts/experimental_design/phase_19_final_evaluation_protocol_freeze.yaml.

**Model Fingerprints**:
- Frozen finalists from Phase 11 (load: random forest, wind: histogram gradient boosting, PV: random forest; B_lags_only feature set), registered with lineage and evaluated once on the sealed partition in Phase 19.

**Feature Fingerprints**:
- B_lags_only: lagged values of the target variable (lags 1, 24, 168 and related blocks); deterministic given the dataset; digests recorded in the lineage report.

**Experiment Protocols**:
1. Data loading from checksummed artifacts (never regenerated).
2. Model loading from the registry (frozen finalists).
3. Inference-only prediction on the sealed final-test partition.
4. Metric computation (MAE, RMSE, sMAPE, nMAE, nRMSE) aligned by timestamp.
5. Artifacts: artifacts/final_evaluation/final_predictions.csv; artifacts/research_tables/final_forecasting_results.csv and final_model_comparison.csv.
6. Lineage reporting in reports/phase_19_final_lineage_report.md.
7. Final-test access record: confirms no training, HPO, feature selection, model selection, or retraining occurred after the protocol freeze.

**Random Seeds**:
- Fixed seed 42 where stochastic (documented in the Phase 19 protocol freeze as seed_hard_coded_in_implementation); frozen models are deterministic at inference.

**Integrity Verification**:
- Post-execution checks confirm models, features, and governance policies are unchanged ("Lineage: PASS", "Governance: UNCHANGED"), and the append-only audit ledger records the evaluation events.

**Notes on Reproducibility**:
- All inputs are checksummed repository artifacts; no synthetic substitution occurs. Research extensions (Stages 07-14 and the live research console) similarly operate on checksummed or user-registered (manifest-documented) datasets only, with chronological splits and no lifecycle mutation.
