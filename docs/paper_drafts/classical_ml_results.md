# Classical ML results draft notes

Validation-only evidence; no final-test result was accessed.

- H24: Random Forest had the lowest classical MAE for load (179.458 MW) and PV (36.588 MW); HistGradientBoosting was lowest for wind (513.907 MW).
- Each H24 best model had lower MAE than its best naive historical reference. RTS DAY_AHEAD remained lower for load (126.613 MW) and wind (269.006 MW). PV daily persistence (33.765 MW) remained lower than the best classical PV model.
- H1 rankings differed: Linear Regression was lowest for load (58.313 MW), Extra Trees for wind (72.012 MW), and HistGradientBoosting for PV (24.964 MW).
- Seed and fold artifacts show that stochastic variation is distinct from fold-to-fold temporal variation. Runtime should be interpreted only in this recorded execution environment.
- Negative raw predictions occur mainly for PV linear/Ridge/HistGradientBoosting configurations; the main metrics retain them without clipping.
