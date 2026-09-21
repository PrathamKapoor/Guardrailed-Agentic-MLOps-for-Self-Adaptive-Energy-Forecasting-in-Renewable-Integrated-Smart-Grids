**Dataset**: We use the RTS-GMLC (Reliability Test System - Grid Modernization Lab Consortium) dataset, which provides synthetic load, wind, and utility-scale PV time series for smart grid forecasting studies. The dataset contains hourly measurements for one year (8,784 hours).

**Targets**: Three forecasting targets are considered:
- Load (electricity demand)
- Wind (wind power generation)
- PV (utility-scale solar photovoltaic generation)

**Forecast Horizon**: 
- Primary: H24 (24-hour ahead forecast)
- Secondary: H1 (1-hour ahead forecast) - for agentic adaptation studies

**Models**: 
- Load: Random Forest with B_lags_only feature set (lagged load values)
- Wind: HistGradientBoosting with B_lags_only feature set (lagged wind values)
- PV: Random Forest with B_lags_only feature set (lagged PV values)
All models are frozen finalists from Phase 11 of the MLOps pipeline competition, representing the best-performing models under resource constraints.

**Features**: 
- B_lags_only: Contains only lagged values of the target variable (e.g., load(t-1), load(t-2), ..., load(t-168) for weekly seasonality).
- No exogenous features are used to isolate the forecasting capability of the autoregressive structure.

**Evaluation Metrics**: 
- Primary: Mean Absolute Error (MAE)
- Secondary: Root Mean Squared Error (RMSE), Symmetric Mean Absolute Percentage Error (sMAPE), Normalized MAE (nMAE), Normalized RMSE (nRMSE)
Metrics are computed over the final test set (the last 20% of the timeline, simulating a holdout period).

**Experimental Protocol**:
1. Load frozen models from the MLflow registry (or qsmlops fallback) for each target.
2. Load actual values and feature rows for the final test set from the artifact store.
3. Generate predictions using the frozen models on the feature rows.
4. Compute metrics by aligning predictions with actual values via timestamps.
5. Save predictions and metrics to artifacts/final_evaluation/ and artifacts/research_tables/.
6. Conduct integrity verification to ensure no modifications to models, features, or governance policies.

**Reproducibility**: 
- Environment: Python 3.13, dependencies as in requirements.txt.
- Random seeds: Fixed where applicable (though frozen models are deterministic).
- Execution command: `python run_phase19_evaluation.py` (or equivalent).
- Data and model fingerprints are recorded in the lineage report.