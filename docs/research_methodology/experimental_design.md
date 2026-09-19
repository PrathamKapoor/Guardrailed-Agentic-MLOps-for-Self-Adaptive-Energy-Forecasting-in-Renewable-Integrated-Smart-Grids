# Experimental design

## Research question and hypotheses

RQ-EXP-1 asks how load, wind, and photovoltaic forecasts should be evaluated temporally so that selection, optimization, and final assessment remain free from future-data leakage. The preregistered hypotheses are: H1, at least one ML approach will reduce out-of-sample error relative to simple persistence for at least one primary target; H2, relative model-family performance will differ by target; H3, combined temporal and historical feature groups will perform differently from calendar-only features. Future H4 concerns drift-aware retraining, and future H5 concerns bounded agentic decision support. None has been evaluated in this phase.

## Forecast horizons and temporal holdout

H24 is primary and conceptually comparable to the external RTS DAY_AHEAD benchmark. H1 is secondary and diagnostic and must not be presented as equivalent to DAY_AHEAD evaluation. Partition membership is assigned by `target_timestamp`: training is 1 January–31 August 2020, validation is 1 September–31 October, and the locked final test is 1 November–31 December. A forecast originating on 31 October with a 1 November target is therefore test data.

Historical features may cross a partition boundary when their source timestamp is no later than the forecast origin. This preserves information that would genuinely have existed in deployment. It does not permit future targets or target-period DAY_AHEAD forecasts as independent-model inputs.

## Rolling-origin validation

Primary model selection uses six expanding-window folds: training begins in January and validation advances monthly from May through October. This preserves order, mimics accumulating operational history, evaluates several periods, and avoids random temporal mixing. It is selected for this study, not claimed universally optimal. Fixed-length rolling windows are reserved for later drift/staleness experiments.

## Final-test isolation and model selection

Rolling-origin validation → aggregate validation performance → compare candidates → select hyperparameters/configuration → freeze configuration → optionally refit that configuration on development data → evaluate once on test. Final-test targets are inaccessible to training/model-selection modes. The final test must remain untouched throughout feature, architecture, threshold, and hyperparameter decisions.

P9-DEV-002 introduced a narrowly scoped `INTEGRITY_AUDIT` exception: the canonical locked load/H24 rows were read solely to deterministically reconstruct, hash, and compare the feature artifact. The exception cannot invoke training, HPO, model selection, prediction, or metric code. Final-test modeling, performance-evaluation, model-selection, and HPO access remain NO; final-test integrity-audit access is YES.

## Baseline protocol and fairness

H1 later supports origin-indexed persistence \(\hat y_{t+1}=y_t\), daily seasonal persistence using the actual at target minus 24 hours, and weekly seasonal persistence using target minus 168 hours when available. H24 supports daily and weekly seasonal persistence defined from explicit target timestamps; the source RTS DAY_AHEAD series is the principal external benchmark. DAY_AHEAD remains excluded from independent-model inputs. Every baseline and model must share identical target timestamps, metrics, and test windows; differing comparison samples must be disclosed. Raw predictions will be evaluated without implicit nonnegative clipping unless a separately declared post-processing experiment is introduced.

## Metrics

For observations \(y_i\) and forecasts \(\hat y_i\), MAE is \(n^{-1}\sum|y_i-\hat y_i|\); RMSE is \(\sqrt{n^{-1}\sum(y_i-\hat y_i)^2}\); sMAPE is \(n^{-1}\sum 200|y_i-\hat y_i|/(|y_i|+|\hat y_i|)\), with a zero contribution when both are zero. nMAE and nRMSE divide their corresponding metric by the mean absolute observed target, consistently across targets. MAE is primary because it remains in the target unit and is less dominated by extreme errors than RMSE. RMSE, sMAPE, nMAE, and nRMSE are secondary. R² is descriptive only. Standard MAPE is not primary for PV because valid zeros make it unstable.

## Stochastic repetition and statistical comparison

Stochastic final experiments use the fixed seeds 42, 123, 2020, 2025, and 31415 and report mean, standard deviation, minimum, and maximum. Deterministic implementations run once unless actual randomness exists. Paired loss sequences will later use a Diebold–Mariano test with horizon-appropriate autocorrelation-aware variance; Wilcoxon signed-rank is secondary where appropriate. Families of tests use Holm–Bonferroni at α=0.05. Practical effects include relative MAE improvement. Temporally meaningful 95% intervals should use a block bootstrap, not naive row resampling.

## Reproducibility and threats

Every later run must record its experiment ID, windows, fold, seed, dataset/feature versions, hyperparameters, metrics, runtime, software version, and checksums. Validation overfitting remains possible under repeated experimentation and is mitigated by predefined families/spaces, rolling origins, a locked test, and later external validation. No model results were inspected to design this protocol.
