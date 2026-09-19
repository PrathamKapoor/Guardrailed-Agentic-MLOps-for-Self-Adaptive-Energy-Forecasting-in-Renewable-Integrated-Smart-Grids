# Evaluation metrics

| Metric | Formula / denominator | Purpose | Limitation | Status |
| --- | --- | --- | --- | --- |
| MAE | mean absolute error | Direct target-unit selection criterion | Does not emphasize extremes | PRIMARY |
| RMSE | square root of mean squared error | Highlights large errors | Sensitive to extremes | SECONDARY |
| sMAPE | mean `200|y-ŷ|/(|y|+|ŷ|)`; 0/0→0 | Scale-relative, zero-safe convention | Can saturate near zero | SECONDARY |
| nMAE | MAE / mean absolute observed target | Cross-target descriptive normalization | Denominator depends on evaluation sample | SECONDARY |
| nRMSE | RMSE / mean absolute observed target | Normalized large-error measure | Same denominator caveat | SECONDARY |
| MAPE | percentage absolute error with safeguards | Optional descriptive comparison | Misleading/undefined near PV zeros | NOT PRIMARY FOR PV |
| R² | explained-variance statistic | Descriptive fit context | Not an error metric | DESCRIPTIVE |
