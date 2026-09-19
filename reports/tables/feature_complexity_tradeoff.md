# Feature complexity tradeoff

| Target | Model | Feature Set | Feature Count | F01-F04 MAE | RMSE | sMAPE | Seed Std | Common Samples |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| load | mlp | A_calendar_only | 6 | 1073.793494 | 1348.579172 | 22.295226 | 246.093075 | 744 |
| load | mlp | C_calendar_lags | 9 | 781.962801 | 986.961152 | 15.714952 | 204.305009 | 744 |
| load | mlp | E_full | 12 | 768.375439 | 985.915992 | 15.366698 | 204.958948 | 744 |
| load | random_forest | A_calendar_only | 6 | 775.714301 | 947.043538 | 16.25986 | 298.519245 | 744 |
| load | random_forest | B_lags_only | 3 | 360.592475 | 477.0259 | 7.317061 | 44.074008 | 744 |
| load | random_forest | C_calendar_lags | 9 | 387.758862 | 532.362872 | 7.736233 | 158.812011 | 744 |
| load | random_forest | D_calendar_lags_rolling | 11 | 398.235948 | 547.900597 | 7.936001 | 158.346003 | 744 |
| load | random_forest | E_full | 12 | 389.306197 | 541.175919 | 7.725817 | 150.763037 | 744 |
| wind | hist_gradient_boosting | A_calendar_only | 6 | 528.290242 | 656.278743 | 104.079166 | 325.505179 | 744 |
| wind | hist_gradient_boosting | B_lags_only | 3 | 527.032874 | 610.137812 | 108.596993 | 70.691303 | 744 |
| wind | hist_gradient_boosting | C_calendar_lags | 9 | 536.989593 | 659.875338 | 105.769383 | 309.932607 | 744 |
| wind | hist_gradient_boosting | D_calendar_lags_rolling | 11 | 575.097737 | 694.392934 | 106.469687 | 383.106025 | 744 |
| wind | hist_gradient_boosting | E_full | 12 | 570.655632 | 690.897805 | 106.244386 | 375.494844 | 744 |
| wind | mlp | A_calendar_only | 6 | 559.719459 | 629.139292 | 110.167656 | 92.61404 | 744 |
| wind | mlp | C_calendar_lags | 9 | 513.694847 | 586.018861 | 108.011439 | 65.820055 | 744 |
| wind | mlp | E_full | 12 | 508.619424 | 579.212368 | 107.935691 | 73.091446 | 744 |
| pv | mlp | A_calendar_only | 6 | 338.37675 | 379.136877 | 121.213527 | 28.760749 | 744 |
| pv | mlp | C_calendar_lags | 9 | 244.088967 | 277.105892 | 110.093134 | 35.855359 | 744 |
| pv | mlp | E_full | 12 | 240.729679 | 277.708804 | 111.641247 | 35.054709 | 744 |
| pv | random_forest | A_calendar_only | 6 | 96.267992 | 131.371071 | 99.735503 | 39.850517 | 744 |
| pv | random_forest | B_lags_only | 3 | 48.004593 | 86.615359 | 90.605799 | 14.579258 | 744 |
| pv | random_forest | C_calendar_lags | 9 | 53.986921 | 89.782571 | 90.991395 | 26.207189 | 744 |
| pv | random_forest | D_calendar_lags_rolling | 11 | 51.869227 | 86.250166 | 90.767132 | 21.289567 | 744 |
| pv | random_forest | E_full | 12 | 49.003184 | 82.921553 | 91.324201 | 19.69291 | 744 |
