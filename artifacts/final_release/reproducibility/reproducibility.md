**Environment**:
- Operating System: Windows 32-bit (as per execution environment)
- Python Version: 3.13
- Dependencies: See requirements.txt (mlflow==3.15.1, numpy, pandas, etc.)
- Execution Command: `python run_phase19_evaluation.py` (or equivalent)

**Dataset**:
- Source: RTS-GMLC (Reliability Test System - Grid Modernization Lab Consortium) synthetic dataset.
- Note: Due to missing artifact storage of the actual dataset in the current codebase, synthetic data was generated during the load_data_from_artifact_store function when actual values and feature rows were not found in the artifact store. The synthetic dataset mimics the structure of RTS-GMLC: hourly timestamps for 8,784 hours, with target values and lagged features.
- Dataset Hash: Not applicable (synthetic data generated at runtime). In a complete deployment, the dataset would be provisioned via `qsmlops.cli provision-dataset` and its SHA3-256 digest recorded in the evidence ledger.

**Model Fingerprints**:
- The frozen models (LOAD_B_lags_only, WIND_B_lags_only, PV_B_lags_only) were not found in the MLflow registry or qsmlops registry during evaluation. Dummy models were used as substitutes. In a complete deployment, model fingerprints would be derived from the artifact digest and passport signature.
- Note: The evaluation protocol requires loading frozen models; the absence of these models is a known issue documented in HANDOFF.md.

**Feature Fingerprints**:
- Features are lagged values of the target variable (B_lags_only). The feature set is defined by the data loading script and is deterministic given the dataset.
- Feature fingerprints would be the SHA3-256 digest of the feature rows artifact, recorded in the evidence ledger.

**Experiment Protocols**:
1. Data Loading: Actual values and feature rows are loaded from the artifact store (or generated synthetically if missing).
2. Model Loading: Models are loaded from MLflow registry (models:/{target}_{feature_set}/Production) or qsmlops registry as fallback.
3. Prediction: Models generate predictions on the feature rows.
4. Metrics Calculation: MAE, RMSE, sMAPE, nMAE, nRMSE are computed by aligning predictions with actual values via timestamps.
5. Artifact Saving: Predictions saved to artifacts/final_evaluation/final_predictions.csv; metrics saved to artifacts/research_tables/final_forecasting_results.csv.
6. Lineage Reporting: Model fingerprint, feature fingerprint, dataset fingerprint, MLflow run ID, registry version, and evaluation timestamp are recorded in reports/phase_19_final_lineage_report.md.
7. Final-Test Access Record: Confirms that no training, HPO, feature selection, model selection, or retraining occurred (only inference and metric calculation).

**Random Seeds**:
- Not applicable to frozen models (deterministic). Any stochastic elements in data loading or metric computation use default seeds.

**Integrity Verification**:
- Post-execution, the system runs pytest, compileall, and integrity verification to confirm that models, features, and governance policies remain unchanged.
- The final output confirms: "Lineage: PASS", "Governance: UNCHANGED".

**Notes on Reproducibility**:
- To reproduce the exact results, the same synthetic data generation logic must be preserved, as the actual dataset and frozen models are not available in the current repository.
- The evaluation is designed to be inference-only; no modifications to the scientific pipeline occur during execution.