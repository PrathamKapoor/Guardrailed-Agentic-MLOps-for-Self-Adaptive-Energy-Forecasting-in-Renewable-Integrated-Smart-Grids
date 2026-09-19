def hourly_mean(values: list[float]) -> float:
    if len(values) != 12: raise ValueError("Hourly five-minute aggregation requires exactly 12 values")
    return sum(values) / 12
