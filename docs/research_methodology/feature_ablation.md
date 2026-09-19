# Feature ablation

Phase 10 evaluates predefined H24 feature families: A calendar, B lags, C calendar+lags, D calendar+lags+rolling, and E full (plus ramp). These are column projections of the frozen Phase 4 `combined_v1` matrix; no new features are engineered. Primary models are the valid Phase 9 selected classical models; secondary robustness models are `PYTORCH_MLP_V1` with frozen Phase 9 configurations. Hyperparameters, folds, metrics, scaling, seed policy, and training policy remain fixed.

F01–F04 rank feature sets by mean MAE. Within 0.5% of the lowest MAE, fewer features are preferred; F05/F06 are post-ablation confirmation only. Every subset uses the common timestamp intersection. The MLP evaluates predefined A/C/E anchors with five seeds. This is an associative feature-group comparison, not feature importance or causal attribution.

No Phase 10 final-test access occurs: training, HPO, model selection, feature selection, and performance evaluation are all NO. The historical integrity-only access remains disclosed as P9-DEV-002 only.
