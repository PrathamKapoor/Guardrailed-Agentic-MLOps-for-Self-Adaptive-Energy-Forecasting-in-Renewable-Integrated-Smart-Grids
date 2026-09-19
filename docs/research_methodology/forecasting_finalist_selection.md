# Forecasting finalist selection

Phase 11 selects one reference internal forecasting configuration per target from VALID development evidence only. F05/F06 mean MAE on matched timestamps is primary; within 0.5% of the best value, simplicity prefers fewer feature columns, then structural complexity, then runtime. F05/F06 remain development data. Paired absolute-error comparisons against predeclared strongest baselines are development-only and Holm-adjusted across the three targets.

The final-test comparison plan is frozen but not executed. Future evaluation requires explicit authorization and must use exact frozen specifications, scaling, training, and seed policies. No ensemble is introduced.
