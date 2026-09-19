from __future__ import annotations

from .base import timestamp_lag_value


def persistence(values, target_timestamp, forecast_origin):
    return timestamp_lag_value(values, target_timestamp, 1, forecast_origin)
