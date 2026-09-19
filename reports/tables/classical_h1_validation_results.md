# Classical H1 validation results

**Secondary validation results only; final test not accessed.**

| target | horizon | model | feature_set | samples | MAE | RMSE | sMAPE | nMAE | nRMSE | best_baseline | best_baseline_MAE | relative_MAE_difference_pct | rts_day_ahead_MAE |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| load | 1 | extra_trees | combined_v1 | 1464 | 78.903919 | 102.081039 | 1.921743 | 0.018531 | 0.023974 | H1_PERSISTENCE | 178.418732 | 55.775989 | None |
| load | 1 | hist_gradient_boosting | combined_v1 | 1464 | 70.640367 | 93.429323 | 1.687750 | 0.016590 | 0.021942 | H1_PERSISTENCE | 178.418732 | 60.407539 | None |
| load | 1 | linear_regression | combined_v1 | 1464 | 58.313493 | 81.662202 | 1.397377 | 0.013695 | 0.019179 | H1_PERSISTENCE | 178.418732 | 67.316496 | None |
| load | 1 | random_forest | combined_v1 | 1464 | 77.808243 | 104.309677 | 1.895588 | 0.018273 | 0.024497 | H1_PERSISTENCE | 178.418732 | 56.390093 | None |
| load | 1 | ridge | combined_v1 | 1464 | 58.466440 | 81.709459 | 1.401210 | 0.013731 | 0.019190 | H1_PERSISTENCE | 178.418732 | 67.230772 | None |
| pv | 1 | extra_trees | combined_v1 | 1464 | 27.330561 | 51.245136 | 107.594363 | 0.066096 | 0.123930 | H1_DAILY_SEASONAL_PERSISTENCE | 33.765096 | 19.056764 | None |
| pv | 1 | hist_gradient_boosting | combined_v1 | 1464 | 24.963556 | 47.030962 | 105.876566 | 0.060371 | 0.113739 | H1_DAILY_SEASONAL_PERSISTENCE | 33.765096 | 26.066977 | None |
| pv | 1 | linear_regression | combined_v1 | 1464 | 68.883063 | 94.815674 | 111.607603 | 0.166585 | 0.229300 | H1_DAILY_SEASONAL_PERSISTENCE | 33.765096 | -104.006716 | None |
| pv | 1 | random_forest | combined_v1 | 1464 | 25.523034 | 51.007450 | 105.208243 | 0.061724 | 0.123355 | H1_DAILY_SEASONAL_PERSISTENCE | 33.765096 | 24.410006 | None |
| pv | 1 | ridge | combined_v1 | 1464 | 68.887660 | 94.813856 | 111.609504 | 0.166596 | 0.229296 | H1_DAILY_SEASONAL_PERSISTENCE | 33.765096 | -104.020333 | None |
| wind | 1 | extra_trees | combined_v1 | 1464 | 72.011736 | 118.826813 | 21.522708 | 0.113553 | 0.187374 | H1_PERSISTENCE | 79.227265 | 9.107381 | None |
| wind | 1 | hist_gradient_boosting | combined_v1 | 1464 | 78.046951 | 124.355457 | 27.219071 | 0.123069 | 0.196091 | H1_PERSISTENCE | 79.227265 | 1.489783 | None |
| wind | 1 | linear_regression | combined_v1 | 1464 | 72.791327 | 116.506902 | 26.187297 | 0.114782 | 0.183715 | H1_PERSISTENCE | 79.227265 | 8.123388 | None |
| wind | 1 | random_forest | combined_v1 | 1464 | 75.084448 | 122.386026 | 20.843842 | 0.118398 | 0.192986 | H1_PERSISTENCE | 79.227265 | 5.229030 | None |
| wind | 1 | ridge | combined_v1 | 1464 | 72.822153 | 116.516965 | 26.215531 | 0.114831 | 0.183731 | H1_PERSISTENCE | 79.227265 | 8.084480 | None |
