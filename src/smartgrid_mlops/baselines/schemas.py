from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class BaselineDefinition:
    baseline_id: str
    horizons: tuple[int, ...]
    lag_hours: int | None
    external: bool = False


@dataclass(frozen=True)
class Prediction:
    experiment_id: str
    baseline_id: str
    target: str
    horizon: int
    fold_id: str
    validation_partition: str
    forecast_origin: datetime
    target_timestamp: datetime
    actual: float
    prediction: float
    absolute_error: float
    squared_error: float
    external_baseline: bool
