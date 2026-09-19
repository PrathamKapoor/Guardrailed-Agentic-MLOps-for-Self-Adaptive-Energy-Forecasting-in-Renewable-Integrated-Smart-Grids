#!/usr/bin/env python3
"""Build canonical hourly and feature artifacts for external OPSD dataset."""
from __future__ import annotations
import hashlib
import json
import math
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pyarrow.csv as pacsv
import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stderr,
)
LOGGER = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data/external/opsd_time_series/time_series_60min_singleindex.csv"
OUT_BASE = ROOT / "data/processed/external/opsd_time_series"

TARGET_MAP = {
    "load": "DE_load_actual_entsoe_transparency",
    "wind": "DE_wind_generation_actual",
    "pv": "DE_solar_generation_actual",
}

def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def load_opsd():
    LOGGER.info("Loading OPSD CSV...")
    # Use pyarrow csv reader, but file is large; use python csv with pandas? Use pyarrow.
    table = pacsv.read_csv(
        str(SRC),
        parse_options=pacsv.ParseOptions(delimiter=","),
        convert_options=pacsv.ConvertOptions(
            strings_can_be_null=True,
            null_values=["", "NA", "nan"],
        ),
    )
    LOGGER.info(f"Columns: {table.schema.names[:5]}... total {len(table.schema.names)}")
    # Extract utc_timestamp and DE columns
    cols = ["utc_timestamp"] + list(TARGET_MAP.values())
    sub = table.select(cols)
    # Convert to python list for processing
    d = sub.to_pydict()
    # Parse timestamps: format 2015-01-01T00:00:00Z
    timestamps = []
    for s in d["utc_timestamp"]:
        if s is None:
            timestamps.append(None)
        elif isinstance(s, datetime):
            # pyarrow already parsed as datetime
            if s.tzinfo is None:
                s = s.replace(tzinfo=timezone.utc)
            timestamps.append(s)
        else:
            # s is string like 2015-01-01T00:00:00Z
            try:
                ts = datetime.fromisoformat(s.replace("Z", "+00:00"))
            except Exception:
                ts = datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            timestamps.append(ts)
    # Build records, drop rows where any target is null
    records = []
    for i, ts in enumerate(timestamps):
        if ts is None:
            continue
        vals = {}
        skip = False
        for target, col in TARGET_MAP.items():
            v = d[col][i]
            if v is None or (isinstance(v, float) and str(v) == "nan"):
                skip = True
                break
            vals[target] = float(v)
        if skip:
            continue
        records.append((ts, vals))
    records.sort(key=lambda x: x[0])
    # Check duplicates
    seen = set()
    dups = 0
    uniq = []
    for ts, vals in records:
        if ts in seen:
            dups += 1
            continue
        seen.add(ts)
        uniq.append((ts, vals))
    LOGGER.info(f"Total valid rows: {len(uniq)} (dups removed {dups}) from {len(records)} parsed")
    if uniq:
        LOGGER.info(f"Coverage: {uniq[0][0]} to {uniq[-1][0]}")
    return uniq

def build_hourly_parquets(records):
    OUT_BASE.mkdir(parents=True, exist_ok=True)
    # Build per-target hourly parquet: timestamp, actual_*
    for target in TARGET_MAP:
        rows = [{"timestamp": ts, f"actual_{target}" if target != "load" else "actual_system_load": vals[target]} for ts, vals in records]
        # But external validation engine expects actual_system_load, actual_wind, actual_pv
        # Use mapping: load->actual_system_load, wind->actual_wind, pv->actual_pv
        col_map = {"load": "actual_system_load", "wind": "actual_wind", "pv": "actual_pv"}
        actual_col = col_map[target]
        table_rows = [{"timestamp": r["timestamp"], actual_col: r[actual_col]} for r in rows]
        table = pa.Table.from_pylist(table_rows)
        out = OUT_BASE / f"{target}_hourly.parquet"
        pq.write_table(table, out)
        LOGGER.info(f"Wrote {out} rows {len(table_rows)} sha {sha(out)[:12]}")
    # Also write combined index
    combined_rows = [{"timestamp": ts, **{f"actual_{k}" if k != "load" else "actual_system_load": v for k, v in vals.items()}} for ts, vals in records]
    # Need to map load column correctly
    for r in combined_rows:
        if "actual_load" in r:
            r["actual_system_load"] = r.pop("actual_load")
    # Actually above already handled load as actual_system_load via vals[target] mapping; combined_rows currently has actual_system_load? Let's rebuild correctly
    combined = []
    for ts, vals in records:
        row = {"timestamp": ts}
        row["actual_system_load"] = vals["load"]
        row["actual_wind"] = vals["wind"]
        row["actual_pv"] = vals["pv"]
        combined.append(row)
    pq.write_table(pa.Table.from_pylist(combined), OUT_BASE / "research_hourly_index.parquet")
    LOGGER.info("Wrote research_hourly_index")
    return combined

def build_features(combined):
    # combined is list of dicts with timestamp and actuals
    # Build per-target feature matrices for h24
    for target in TARGET_MAP:
        col = {"load": "actual_system_load", "wind": "actual_wind", "pv": "actual_pv"}[target]
        y = [r[col] for r in combined]
        ts = [r["timestamp"] for r in combined]
        maxlook = max(1,24,168,24,168)
        horizon = 24
        rows = []
        for i in range(maxlook, len(y) - horizon):
            o = ts[i]
            # calendar from origin
            hour = o.hour
            dow = o.weekday()
            doy = o.timetuple().tm_yday
            row = {
                "forecast_origin": o,
                "target_timestamp": ts[i + horizon],
                "hour_sin": math.sin(2*math.pi*hour/24),
                "hour_cos": math.cos(2*math.pi*hour/24),
                "dow_sin": math.sin(2*math.pi*dow/7),
                "dow_cos": math.cos(2*math.pi*dow/7),
                "doy_sin": math.sin(2*math.pi*doy/366),
                "doy_cos": math.cos(2*math.pi*doy/366),
                "lag_1": y[i-1] if i-1 >=0 else None,
                "lag_24": y[i-24],
                "lag_168": y[i-168],
                "rolling_mean_24": sum(y[i-24:i])/24,
                "rolling_mean_168": sum(y[i-168:i])/168,
                "ramp_1h": y[i] - y[i-1],
                "target": y[i+horizon],
            }
            rows.append(row)
        out = OUT_BASE / "features" / target / "h24" / "combined_v1.parquet"
        out.parent.mkdir(parents=True, exist_ok=True)
        # Remove None checks (should not have)
        pq.write_table(pa.Table.from_pylist(rows), out, compression="zstd", use_dictionary=False)
        LOGGER.info(f"Features {target} h24: {len(rows)} rows sha {sha(out)[:12]}")

if __name__ == "__main__":
    records = load_opsd()
    combined = build_hourly_parquets(records)
    build_features(combined)
    LOGGER.info("DONE")
