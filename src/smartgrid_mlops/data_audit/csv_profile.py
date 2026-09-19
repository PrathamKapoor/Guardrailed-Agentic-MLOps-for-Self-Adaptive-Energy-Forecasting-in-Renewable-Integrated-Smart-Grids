"""Deterministic CSV/time-series structural profiling."""

from __future__ import annotations

import csv
import math
import statistics
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from .timestamp_audit import continuity_summary, expected_periods, reconstruct_timestamp


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    low, high = int(position), min(int(position) + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


class NumericStats:
    def __init__(self) -> None:
        self.count = self.zero = self.negative = self.nonfinite = self.nan = self.infinite = 0
        self.minimum = math.inf
        self.maximum = -math.inf
        self.mean = self.m2 = 0.0
        self.values: list[float] = []

    def add(self, value: float) -> None:
        if not math.isfinite(value):
            self.nonfinite += 1
            self.nan += math.isnan(value)
            self.infinite += math.isinf(value)
            return
        self.count += 1
        self.zero += value == 0
        self.negative += value < 0
        self.minimum, self.maximum = min(self.minimum, value), max(self.maximum, value)
        delta = value - self.mean
        self.mean += delta / self.count
        self.m2 += delta * (value - self.mean)
        self.values.append(value)

    def result(self, include_percentiles: bool = False) -> dict[str, Any]:
        output: dict[str, Any] = {
            "count": self.count, "min": self.minimum if self.count else None,
            "max": self.maximum if self.count else None, "mean": self.mean if self.count else None,
            "stddev": math.sqrt(self.m2 / self.count) if self.count else None,
            "zero_count": self.zero, "zero_percentage": (100 * self.zero / self.count) if self.count else None,
            "negative_count": self.negative, "nonfinite_count": self.nonfinite, "nan_count": self.nan, "infinite_count": self.infinite,
        }
        if include_percentiles:
            output.update({"median": percentile(self.values, .5), "p01": percentile(self.values, .01), "p99": percentile(self.values, .99), "q1": percentile(self.values, .25), "q3": percentile(self.values, .75)})
        return output


def profile_timeseries(path: Path, category: str, resolution_minutes: int, include_series_percentiles: bool = False) -> dict[str, Any]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        fields = reader.fieldnames or []
        value_columns = [field for field in fields if field not in {"Year", "Month", "Day", "Period"}]
        series = {field: NumericStats() for field in value_columns}
        aggregate = NumericStats()
        rows, missing_cells, missing_rows, duplicate_rows = 0, 0, 0, 0
        prior_rows: set[tuple[str, ...]] = set()
        timestamps: list[datetime] = []
        aggregate_values: list[tuple[datetime, float]] = []
        periods: set[int] = set()
        hour_sums = [0.0] * 24
        hour_counts = [0] * 24
        aggregate_min: tuple[datetime, float] | None = None
        aggregate_max: tuple[datetime, float] | None = None
        for row in reader:
            rows += 1
            raw = tuple(row.get(field, "") for field in fields)
            duplicate_rows += raw in prior_rows
            prior_rows.add(raw)
            if not any(raw):
                missing_rows += 1
                continue
            try:
                period = int(row["Period"])
                periods.add(period)
                timestamp = reconstruct_timestamp(int(row["Year"]), int(row["Month"]), int(row["Day"]), period, resolution_minutes)
                timestamps.append(timestamp)
            except (KeyError, TypeError, ValueError):
                missing_rows += 1
                continue
            row_values: list[float] = []
            for field in value_columns:
                cell = row.get(field, "").strip()
                if not cell:
                    missing_cells += 1
                    continue
                try:
                    value = float(cell)
                except ValueError:
                    missing_cells += 1
                    continue
                series[field].add(value)
                row_values.append(value)
            if len(row_values) == len(value_columns):
                total = sum(row_values)
                aggregate.add(total)
                aggregate_values.append((timestamp, total))
                if aggregate_min is None or total < aggregate_min[1]: aggregate_min = (timestamp, total)
                if aggregate_max is None or total > aggregate_max[1]: aggregate_max = (timestamp, total)
                hour_sums[timestamp.hour] += total
                hour_counts[timestamp.hour] += 1
        continuity = continuity_summary(timestamps, resolution_minutes)
        deltas = [(current[1] - previous[1], current[0]) for previous, current in zip(aggregate_values, aggregate_values[1:])]
        largest_up = max(deltas, default=(None, None), key=lambda item: item[0] if item[0] is not None else -math.inf)
        largest_down = min(deltas, default=(None, None), key=lambda item: item[0] if item[0] is not None else math.inf)
        date_counts = Counter(timestamp.date().isoformat() for timestamp in timestamps)
        temporal = {
            "first_timestamp": timestamps[0].isoformat() if timestamps else None,
            "last_timestamp": timestamps[-1].isoformat() if timestamps else None,
            "year_range": [min((stamp.year for stamp in timestamps), default=None), max((stamp.year for stamp in timestamps), default=None)],
            "month_range": [min((stamp.month for stamp in timestamps), default=None), max((stamp.month for stamp in timestamps), default=None)],
            "period_range": [min(periods) if periods else None, max(periods) if periods else None],
            "expected_periods_per_day": expected_periods(resolution_minutes),
            "specific_date_period_counts": {date: date_counts.get(date, 0) for date in ("2020-01-01", "2020-02-28", "2020-02-29", "2020-03-01", "2020-12-31")},
            **continuity,
        }
        result = {
            "relative_path": path.as_posix(), "category": category, "resolution_minutes": resolution_minutes,
            "rows": rows, "columns": len(fields), "column_names": fields, "value_columns": value_columns,
            "missing_cells": missing_cells, "missing_rows": missing_rows, "duplicate_rows": duplicate_rows,
            "negative_values": sum(item.negative for item in series.values()), "zero_values": sum(item.zero for item in series.values()),
            "infinite_values": sum(item.infinite for item in series.values()), "nan_values": sum(item.nan for item in series.values()), "temporal": temporal,
            "series": {key: value.result(include_series_percentiles) for key, value in series.items()},
            "constant_columns": [key for key, value in series.items() if value.count and value.minimum == value.maximum],
            "all_zero_columns": [key for key, value in series.items() if value.count and value.zero == value.count],
            "unexpectedly_sparse_columns": [key for key, value in series.items() if value.count and value.zero / value.count > .95 and category not in {"pv", "rtpv"}],
            "aggregate": aggregate.result(True), "aggregate_first_values": [(timestamp.isoformat(), value) for timestamp, value in aggregate_values[:2016]],
            "aggregate_minimum_timestamp": aggregate_min[0].isoformat() if aggregate_min else None,
            "aggregate_maximum_timestamp": aggregate_max[0].isoformat() if aggregate_max else None,
            "average_aggregate_by_hour": [hour_sums[hour] / hour_counts[hour] if hour_counts[hour] else None for hour in range(24)],
            "largest_positive_ramp": {"value": largest_up[0], "timestamp": largest_up[1].isoformat() if largest_up[1] else None},
            "largest_negative_ramp": {"value": largest_down[0], "timestamp": largest_down[1].isoformat() if largest_down[1] else None},
        }
    return result
