# Stage 9 Research Report

Generated: `2026-09-05T07:34:45.371180+00:00`

Total candidates evaluated: **9**

## Classification totals

- `IMPROVED`: 6
- `NO_MEANINGFUL_IMPROVEMENT`: 1
- `REGRESSED`: 2

## Per-candidate results

| candidate_id | target | MAE | RMSE | sMAPE (%) | n | classification | notes |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| `baseline_H24_PERSISTENCE_pv` | pv | 39.095 | 100.692 | 3.93 | 1464 | **REGRESSED** | Re-derivation of the existing frozen baseline metrics compared against the frozen final-test finalist for the same target.; frozen finalist MAE=36.12. |
| `baseline_RTS_DAY_AHEAD_load` | load | 101.142 | 101.845 | 1.36 | 1464 | **IMPROVED** | Re-derivation of the existing frozen baseline metrics compared against the frozen final-test finalist for the same target.; frozen finalist MAE=174.26. |
| `baseline_RTS_DAY_AHEAD_wind` | wind | 331.302 | 491.208 | 25.46 | 1464 | **IMPROVED** | Re-derivation of the existing frozen baseline metrics compared against the frozen final-test finalist for the same target.; frozen finalist MAE=778.84. |
| `bias_corrected_hist_gradient_boosting_wind` | wind | 765.944 | 882.984 | 43.13 | 1464 | **IMPROVED** |  |
| `bias_corrected_random_forest_load` | load | 173.190 | 231.025 | 2.34 | 1464 | **NO_MEANINGFUL_IMPROVEMENT** |  |
| `bias_corrected_random_forest_pv` | pv | 39.550 | 81.816 | 58.97 | 1464 | **REGRESSED** |  |
| `blend_hist_gradient_boosting_RTS_DAY_AHEAD_a0.50_wind` | wind | 475.849 | 572.823 | 34.41 | 1464 | **IMPROVED** | ; frozen finalist MAE=778.84. |
| `blend_random_forest_H24_DAILY_PERSISTENCE_a0.50_pv` | pv | 34.373 | 84.018 | 58.16 | 1464 | **IMPROVED** | ; frozen finalist MAE=36.12. |
| `blend_random_forest_RTS_DAY_AHEAD_a0.50_load` | load | 100.334 | 126.193 | 1.38 | 1464 | **IMPROVED** | ; frozen finalist MAE=174.26. |
