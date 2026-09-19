from __future__ import annotations

import hashlib, json
from datetime import datetime
from pathlib import Path
import pyarrow.parquet as pq
from .protocol import partition_for_timestamp

def load_feature_rows(path: Path) -> list[dict]:
    return pq.read_table(path, columns=["forecast_origin", "target_timestamp"]).to_pylist()

def split_rows(rows: list[dict]) -> dict[str, list[dict]]:
    result={"TRAIN":[],"VALIDATION":[],"TEST":[]}
    for row in rows:
        partition=partition_for_timestamp(row["target_timestamp"])
        if partition in result: result[partition].append(row)
    return result

def stable_checksum(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()
