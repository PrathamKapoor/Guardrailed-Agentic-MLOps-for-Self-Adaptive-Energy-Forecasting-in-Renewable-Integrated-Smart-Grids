# Experiment naming and metadata

IDs use `TARGET-HORIZON-MODEL-FEATURESET-SEED-FOLD`, for example `LOAD-H24-RF-FULLV1-S42-F03`. `DET` replaces the seed token for deterministic runs. Target is LOAD/WIND/PV; horizon is H1/H24; model and feature-set abbreviations must be documented in the run metadata; folds are F01–F06.

Every run records: `experiment_id`, target, horizon, model family, feature set, dataset version, feature version, training/validation/test windows, fold ID, seed, hyperparameters, metrics, runtime, software version, and artifact checksum. Test-window metadata may be recorded before final evaluation, but locked test targets/metrics may not be exposed until the configuration is frozen.
