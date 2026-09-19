from __future__ import annotations

from datetime import datetime


def reject_final_test(timestamp: datetime) -> None:
    if timestamp >= datetime(2020, 11, 1): raise PermissionError("Classical model-selection mode cannot access locked final-test targets")
