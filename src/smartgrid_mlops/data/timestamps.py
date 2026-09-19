from datetime import datetime, timedelta

def timestamp(year: int, month: int, day: int, period: int, minutes: int) -> datetime:
    if period < 1 or 1440 % minutes: raise ValueError("invalid one-based period or resolution")
    if period > 1440 // minutes: raise ValueError("period exceeds day resolution")
    return datetime(year, month, day) + timedelta(minutes=(period - 1) * minutes)
