# Statistical analysis plan

This plan was frozen before model results. MAE is the primary loss criterion. Paired absolute- and squared-error sequences may be compared using the Diebold–Mariano test when its assumptions are appropriate, with an autocorrelation-aware long-run variance estimate selected in advance for the forecast horizon. Wilcoxon signed-rank is a secondary paired analysis, not a mechanism for significance searching.

The familywise significance level is α=0.05 and related comparisons use Holm–Bonferroni correction. Statistical significance must be accompanied by practical effect, including `100 × (MAE_baseline − MAE_model) / MAE_baseline` and, where useful, the analogous RMSE quantity. For temporally dependent metric intervals, later work should use a documented block bootstrap and report 95% confidence intervals. No test, correction, or interval was run in Phase 5.
