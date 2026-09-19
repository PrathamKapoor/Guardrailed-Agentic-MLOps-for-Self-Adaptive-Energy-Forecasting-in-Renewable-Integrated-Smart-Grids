from __future__ import annotations

from .base import timestamp_lag_value


def daily(values, target_timestamp, forecast_origin):
    return timestamp_lag_value(values, target_timestamp, 24, forecast_origin)


def weekly(values, target_timestamp, forecast_origin):
    return timestamp_lag_value(values, target_timestamp, 168, forecast_origin)
