# Forecast availability contract

For `X_t → y_(t+h)`, h is 1 or 24 hours. Calendar/cyclical features are derived from `forecast_origin` and are available for both horizons. Lags `y(t-k)`, rolling means over `[t-w,t-1]`, and `y(t)-y(t-1)` ramps are available at or before the origin and are allowed for both horizons. `DAY_AHEAD` values at target time are forbidden from independent ML feature matrices and reserved as external baselines. Scaling is not applied globally.
