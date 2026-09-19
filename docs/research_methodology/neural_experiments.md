# Neural experiments

Phase 8 evaluates an MLP tabular track using `combined_v1` and LSTM/GRU sequence tracks using a 168-hour historical target/calendar sequence plus target-time known calendar features. All models are compact, direct point forecasters for H1/H24. Inputs and targets are StandardScaler-transformed within each outer training fold only; outputs are inverse transformed before metrics. Adam (0.001), MSE loss, batch size 64, maximum 12 epochs, and inner chronological 10% early stopping (patience 4) were frozen before official results. LSTM/GRU are unidirectional, have hidden size 32, and use gradient clipping at 1.0.

Six frozen expanding folds were used. H24 uses all five preregistered seeds; H1 is a formally reduced secondary seed-42 replication due to measured CPU cost. Sequence-model comparisons with classical tabular models differ in input representation and cannot isolate architecture alone. Raw negative forecasts remain un-clipped. Final test is inaccessible.
