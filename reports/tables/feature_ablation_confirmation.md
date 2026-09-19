# Post-ablation confirmation

| Target | Model | Selected Feature Set | F01-F04 selection MAE | F05 MAE | F06 MAE | F05-F06 mean MAE |
| --- | --- | --- | --- | --- | --- | --- |
| load | random_forest | B_lags_only | 360.592475 | 338.49448 | 233.437077 | 285.965778 |
| wind | hist_gradient_boosting | B_lags_only | 527.032874 | 541.272254 | 515.953975 | 528.613115 |
| pv | random_forest | B_lags_only | 48.004593 | 37.414504 | 50.718056 | 44.06628 |
| load | mlp | E_full | 768.375439 | 578.49552 | 386.697132 | 482.596326 |
| wind | mlp | E_full | 508.619424 | 524.22946 | 540.60454 | 532.417 |
| pv | mlp | E_full | 240.729679 | 250.98715 | 237.237498 | 244.112324 |
