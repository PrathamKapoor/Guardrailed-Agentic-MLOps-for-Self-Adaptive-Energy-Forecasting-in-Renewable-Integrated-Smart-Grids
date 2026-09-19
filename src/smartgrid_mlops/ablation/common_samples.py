from __future__ import annotations
from collections.abc import Iterable

def common_timestamp_intersection(feature_rows: dict[str, Iterable[dict]]) -> set[tuple]:
    sets=[{(row['forecast_origin'],row['target_timestamp']) for row in rows} for rows in feature_rows.values()]
    return set.intersection(*sets) if sets else set()
