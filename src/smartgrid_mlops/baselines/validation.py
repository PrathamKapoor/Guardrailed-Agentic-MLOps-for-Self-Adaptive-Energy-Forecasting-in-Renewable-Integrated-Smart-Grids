from __future__ import annotations

from datetime import datetime


def ensure_validation_only(timestamp: datetime) -> None:
    if timestamp >= datetime(2020, 11, 1):
        raise PermissionError("Phase 6 baseline execution cannot access locked final-test timestamps")


def ensure_identical_timestamps(expected, observed) -> None:
    if list(expected) != list(observed):
        raise ValueError("baseline timestamps do not match eligible feature-matrix timestamps")
