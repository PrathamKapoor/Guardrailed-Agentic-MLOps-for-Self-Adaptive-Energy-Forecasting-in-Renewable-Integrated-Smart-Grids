# Drift detector configuration

|Detector|Reference|Statistic|Normalization|Threshold|Window|Stride|Role|
|---|---|---|---|---|---|---|---|
|Feature|F01-F03|PSI + normalized Wasserstein|IQR fallback|99th percentile|168 h|24 h|development|
|Prediction|F01-F03|normalized Wasserstein|IQR fallback|frozen|168 h|24 h|development|
|Performance|F01-F03|rolling MAE + error distance|calibration MAE|frozen|168 h|24 h|development|
|Data quality|schema reference|missing/NaN/Inf|deterministic|critical|168 h|24 h|development|
