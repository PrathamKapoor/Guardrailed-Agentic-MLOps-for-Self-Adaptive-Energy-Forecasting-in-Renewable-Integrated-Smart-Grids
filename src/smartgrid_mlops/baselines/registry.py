from __future__ import annotations

from .schemas import BaselineDefinition

H1_PERSISTENCE = BaselineDefinition("H1_PERSISTENCE", (1,), 1)
H1_DAILY = BaselineDefinition("H1_DAILY_SEASONAL_PERSISTENCE", (1,), 24)
H1_WEEKLY = BaselineDefinition("H1_WEEKLY_SEASONAL_PERSISTENCE", (1,), 168)
H24_DAILY = BaselineDefinition("H24_DAILY_PERSISTENCE", (24,), 24)
H24_WEEKLY = BaselineDefinition("H24_WEEKLY_SEASONAL_PERSISTENCE", (24,), 168)
RTS_DAY_AHEAD = BaselineDefinition("RTS_DAY_AHEAD", (24,), None, external=True)


def definitions_for(horizon: int) -> tuple[BaselineDefinition, ...]:
    return (H1_PERSISTENCE, H1_DAILY, H1_WEEKLY) if horizon == 1 else (H24_DAILY, H24_WEEKLY, RTS_DAY_AHEAD)
