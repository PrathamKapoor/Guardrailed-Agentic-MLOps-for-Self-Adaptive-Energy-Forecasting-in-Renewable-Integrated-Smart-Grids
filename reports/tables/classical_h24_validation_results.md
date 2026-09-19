# Classical H24 validation results

**Validation only; final test not accessed.**

| target | horizon | model | feature_set | samples | MAE | RMSE | sMAPE | nMAE | nRMSE | best_baseline | best_baseline_MAE | relative_MAE_difference_pct | rts_day_ahead_MAE |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| load | 24 | extra_trees | combined_v1 | 1464 | 182.940116 | 249.014942 | 4.135787 | 0.042964 | 0.058482 | H24_DAILY_PERSISTENCE | 211.392251 | 13.459403 | 126.613062 |
| load | 24 | hist_gradient_boosting | combined_v1 | 1464 | 207.943580 | 290.659736 | 4.703538 | 0.048836 | 0.068262 | H24_DAILY_PERSISTENCE | 211.392251 | 1.631409 | 126.613062 |
| load | 24 | linear_regression | combined_v1 | 1464 | 259.513624 | 327.267560 | 6.111068 | 0.060947 | 0.076859 | H24_DAILY_PERSISTENCE | 211.392251 | -22.764019 | 126.613062 |
| load | 24 | random_forest | combined_v1 | 1464 | 179.458322 | 249.660554 | 4.054660 | 0.042146 | 0.058633 | H24_DAILY_PERSISTENCE | 211.392251 | 15.106480 | 126.613062 |
| load | 24 | ridge | combined_v1 | 1464 | 259.502238 | 327.241562 | 6.110609 | 0.060945 | 0.076853 | H24_DAILY_PERSISTENCE | 211.392251 | -22.758633 | 126.613062 |
| pv | 24 | extra_trees | combined_v1 | 1464 | 38.989785 | 78.190523 | 105.667092 | 0.094292 | 0.189094 | H24_DAILY_PERSISTENCE | 33.765096 | -15.473641 | 48.795446 |
| pv | 24 | hist_gradient_boosting | combined_v1 | 1464 | 42.006308 | 84.605341 | 106.510031 | 0.101587 | 0.204608 | H24_DAILY_PERSISTENCE | 33.765096 | -24.407489 | 48.795446 |
| pv | 24 | linear_regression | combined_v1 | 1464 | 45.659108 | 75.922614 | 106.752850 | 0.110421 | 0.183609 | H24_DAILY_PERSISTENCE | 33.765096 | -35.225764 | 48.795446 |
| pv | 24 | random_forest | combined_v1 | 1464 | 36.588211 | 76.117961 | 104.410329 | 0.088484 | 0.184082 | H24_DAILY_PERSISTENCE | 33.765096 | -8.361046 | 48.795446 |
| pv | 24 | ridge | combined_v1 | 1464 | 45.699622 | 75.947788 | 106.764281 | 0.110519 | 0.183670 | H24_DAILY_PERSISTENCE | 33.765096 | -35.345749 | 48.795446 |
| wind | 24 | extra_trees | combined_v1 | 1464 | 538.530772 | 649.134464 | 98.457834 | 0.849189 | 1.023596 | H24_DAILY_PERSISTENCE | 586.542276 | 8.185515 | 269.005652 |
| wind | 24 | hist_gradient_boosting | combined_v1 | 1464 | 513.906500 | 676.417530 | 100.293935 | 0.810360 | 1.066617 | H24_DAILY_PERSISTENCE | 586.542276 | 12.383724 | 269.005652 |
| wind | 24 | linear_regression | combined_v1 | 1464 | 531.050407 | 635.904197 | 98.899596 | 0.837393 | 1.002733 | H24_DAILY_PERSISTENCE | 586.542276 | 9.460847 | 269.005652 |
| wind | 24 | random_forest | combined_v1 | 1464 | 541.100515 | 712.273826 | 98.769174 | 0.853241 | 1.123158 | H24_DAILY_PERSISTENCE | 586.542276 | 7.747397 | 269.005652 |
| wind | 24 | ridge | combined_v1 | 1464 | 531.039609 | 635.902896 | 98.899941 | 0.837376 | 1.002731 | H24_DAILY_PERSISTENCE | 586.542276 | 9.462688 | 269.005652 |
