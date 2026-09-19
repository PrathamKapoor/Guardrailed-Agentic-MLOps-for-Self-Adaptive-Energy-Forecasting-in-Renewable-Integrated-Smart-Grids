from __future__ import annotations

from datetime import datetime, timedelta


def timestamp_lag_value(values: dict[datetime, float], target_timestamp: datetime, lag_hours: int, forecast_origin: datetime) -> tuple[float, datetime]:
    source_timestamp = target_timestamp - timedelta(hours=lag_hours)
    if source_timestamp > forecast_origin:
        raise ValueError("baseline source occurs after forecast origin")
    if source_timestamp not in values:
        raise KeyError(f"missing timestamp for baseline source: {source_timestamp.isoformat()}")
    return values[source_timestamp], source_timestamp
