# Final results (Phase 19)

Final-test window: 2020-11-01 to 2020-12-31, 1464 hourly observations per target.
Configurations: frozen reference (Phase 11 finalist), MLP challenger (Phase 9 HPO
best, 5-seed ensemble), and the frozen external benchmark (RTS_DAY_AHEAD for
LOAD/WIND; H24_DAILY_PERSISTENCE for PV). All numbers come from
`artifacts/experiments/final_evaluation/phase_19/official/` and the spec-named
research tables.

## Per-configuration MAE on final test

| Target | Frozen reference | MLP challenger | External benchmark | MAE best |
| ---    | ---              | ---            | ---                | ---      |
| load   | 174.26 (random_forest, B_lags_only) | 281.00 (mlp, E_full, 5-seed) | **101.14** (RTS_DAY_AHEAD) | benchmark |
| wind   | 778.84 (hist_gradient_boosting, B_lags_only) | 838.40 (mlp, E_full, 5-seed) | **331.30** (RTS_DAY_AHEAD) | benchmark |
| pv     | **36.12** (random_forest, B_lags_only) | 221.64 (mlp, E_full, 5-seed) | 39.09 (H24_DAILY_PERSISTENCE) | frozen reference |

## Per-configuration full metrics

| Target | Configuration        | MAE     | RMSE    | sMAPE   | nMAE    | nRMSE   |
| ---    | ---                  | ---     | ---     | ---     | ---     | ---     |
| load   | reference (RF)       | 174.257 | 231.271 |   4.717 | 0.0474  | 0.0628  |
| load   | challenger (MLP)     | 281.001 | 343.359 |   7.777 | 0.0764  | 0.0933  |
| load   | RTS_DAY_AHEAD        | 101.142 | 101.845 |   2.717 | 0.0275  | 0.0277  |
| wind   | reference (HistGB)   | 778.841 | 923.373 |  92.397 | 0.6790  | 0.8050  |
| wind   | challenger (MLP)     | 838.401 | 957.930 |  96.131 | 0.7309  | 0.8351  |
| wind   | RTS_DAY_AHEAD        | 331.302 | 491.208 |  50.916 | 0.2888  | 0.4282  |
| pv     | reference (RF)       |  36.122 |  82.079 | 117.735 | 0.1082  | 0.2458  |
| pv     | challenger (MLP)     | 221.640 | 244.103 | 135.468 | 0.6639  | 0.7310  |
| pv     | H24_DAILY_PERSISTENCE |  39.095 | 110.825 |   7.863 | 0.1171  | 0.3320  |

## Frozen model vs external benchmark

| Target | Frozen model MAE | External benchmark | Benchmark MAE | Δ absolute | Δ relative |
| ---    | ---              | ---                | ---          | ---        | ---        |
| load   | 174.26          | RTS_DAY_AHEAD      | 101.14       | +73.11     |  +72.29%   |
| wind   | 778.84          | RTS_DAY_AHEAD      | 331.30       | +447.54    | +135.08%   |
| pv     |  36.12          | H24_DAILY_PERSISTENCE |  39.09    |  −2.97     |   −7.61%   |

## Interpretation (registered analyses only)

- The frozen ML reference models generalize (MAE finite on all targets) and
  reproduce the registered pre-test signal: PV's random_forest beats daily
  persistence; LOAD and WIND development models are dominated by the
  published RTS day-ahead forecast on this 2-month window.
- The MLP challenger underperforms the frozen reference on all three targets;
  it would not be eligible for promotion under the Phase 16 policy (its
  benchmark gate fails), so the champion-challenger + rollback layer would
  block the swap.
- The Diebold-Mariano and Holm-Bonferroni families were computed inside the
  engine (`metrics/holm_bonferroni.json`) — reported as supporting evidence,
  not as new hypothesis tests.

## Lifecycle outcomes

Phase 19 produced zero promotions, zero challengers, zero governance state
changes, and zero rollback events. The lifecycle registry, the Phase 13
governance policy, the Phase 15 retraining policy, the Phase 16 promotion
policy, and all 19 protocol freeze checksums remain byte-identical to the
pre-final state.
