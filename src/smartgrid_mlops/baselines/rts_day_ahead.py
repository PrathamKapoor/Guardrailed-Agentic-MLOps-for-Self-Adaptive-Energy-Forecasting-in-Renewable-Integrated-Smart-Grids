from __future__ import annotations


def day_ahead_value(values, target_timestamp):
    if target_timestamp not in values:
        raise KeyError(f"missing RTS DAY_AHEAD timestamp: {target_timestamp.isoformat()}")
    return values[target_timestamp]
