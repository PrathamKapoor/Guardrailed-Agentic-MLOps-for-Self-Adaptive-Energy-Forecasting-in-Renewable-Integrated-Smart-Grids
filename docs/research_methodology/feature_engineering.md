# Leakage-safe feature engineering

RQ-FEAT-1 asks which calendar, autoregressive, and rolling-history groups provide valid predictive information without temporal leakage. H-FEAT-1 is an untested expectation that combining these groups can outperform calendar-only or persistence information.

Features use a forecast-origin contract: `X_t → y_(t+h)`, where `h ∈ {1,24}`. H24 is primary because RTS-GMLC provides day-ahead forecasts; H1 is secondary diagnostic. Calendar features use sine/cosine encodings of hour (24), weekday (7), and day-of-year (366). Historical features are `L_k(t)=y(t-k)`, rolling mean `μ_w(t)=w⁻¹Σᵢ₌₁ʷy(t-i)`, and a one-hour ramp. All exclude future values. No weather or cross-target covariates are used; PV nighttime zeros are retained.
