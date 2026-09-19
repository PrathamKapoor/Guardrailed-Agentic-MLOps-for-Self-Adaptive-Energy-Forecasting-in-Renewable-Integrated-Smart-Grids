"""Timestamp reconstruction and continuity checks; no source data mutation."""

from __future__ import annotations

from datetime import datetime, timedelta


def reconstruct_timestamp(year: int, month: int, day: int, period: int, resolution_minutes: int) -> datetime:
    if period < 1:
        raise ValueError("Period must be one-based")
    return datetime(year, month, day) + timedelta(minutes=(period - 1) * resolution_minutes)


def expected_periods(resolution_minutes: int) -> int:
    if 1440 % resolution_minutes:
        raise ValueError("Resolution must divide one day")
    return 1440 // resolution_minutes


def continuity_summary(timestamps: list[datetime], resolution_minutes: int) -> dict[str, int | bool]:
    if not timestamps:
        return {"duplicate_timestamps": 0, "missing_intervals": 0, "out_of_order": False}
    duplicates = len(timestamps) - len(set(timestamps))
    missing = 0
    out_of_order = False
    step = timedelta(minutes=resolution_minutes)
    for previous, current in zip(timestamps, timestamps[1:]):
        if current <= previous:
            out_of_order = True
        elif current - previous > step:
            missing += int((current - previous) / step) - 1
    return {"duplicate_timestamps": duplicates, "missing_intervals": missing, "out_of_order": out_of_order}
