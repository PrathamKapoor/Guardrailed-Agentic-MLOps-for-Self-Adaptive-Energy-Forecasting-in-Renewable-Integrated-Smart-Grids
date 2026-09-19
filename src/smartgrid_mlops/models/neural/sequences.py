from __future__ import annotations
from datetime import timedelta

CALENDAR=("hour_sin","hour_cos","dow_sin","dow_cos","doy_sin","doy_cos")

def build_sequences(feature_rows, actual_by_timestamp, length=168):
    """Historical target/calendar sequences ending at origin, plus legal target-time calendar."""
    indexed={r["forecast_origin"]:r for r in feature_rows}; output=[]
    for row in feature_rows:
        origin=row["forecast_origin"]; history=[]; valid=True
        for offset in range(length-1,-1,-1):
            source=origin-timedelta(hours=offset); source_row=indexed.get(source)
            if source_row is None or source>origin or source not in actual_by_timestamp: valid=False; break
            history.append([actual_by_timestamp[source],*[source_row[k] for k in CALENDAR]])
        if valid: output.append({"sequence":history,"future_calendar":[row[k] for k in CALENDAR],"forecast_origin":origin,"target_timestamp":row["target_timestamp"]})
    return output
