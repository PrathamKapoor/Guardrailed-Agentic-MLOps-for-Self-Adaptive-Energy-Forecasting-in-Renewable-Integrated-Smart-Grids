# Baseline results draft notes

Development/validation findings only; these are not final-test results.

- H1: persistence had the lowest MAE for load (178.419 MW) and wind (79.227 MW); daily seasonal persistence was lowest for PV (33.765 MW).
- H24 historical: daily persistence had lower MAE than weekly persistence for load (211.392 MW), wind (586.542 MW), and PV (33.765 MW).
- RTS DAY_AHEAD had lower H24 MAE than historical rules for load (126.613 MW) and wind (269.006 MW). For PV, H24 daily persistence was lower (33.765 MW) than RTS DAY_AHEAD (48.795 MW).
- Fold-level differences are descriptive temporal variation rather than stochastic variance. Target-specific patterns are consistent with different temporal structure; causal explanations require further validation.
