import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from smartgrid_mlops.data.aggregation import hourly_mean
from smartgrid_mlops.data.alignment import validate_alignment
from smartgrid_mlops.data.timestamps import timestamp


def test_canonical_timestamp_boundaries() -> None:
    assert timestamp(2020, 1, 1, 1, 60).isoformat() == "2020-01-01T00:00:00"
    assert timestamp(2020, 2, 28, 24, 60).isoformat() == "2020-02-28T23:00:00"
    assert timestamp(2020, 2, 29, 1, 60).isoformat() == "2020-02-29T00:00:00"
    assert timestamp(2020, 3, 1, 1, 60).isoformat() == "2020-03-01T00:00:00"
    assert timestamp(2020, 12, 31, 288, 5).isoformat() == "2020-12-31T23:55:00"


def test_hourly_power_mean_preserves_physical_quantity() -> None:
    assert hourly_mean([100.0] * 12) == 100.0
    assert hourly_mean([float(value) for value in range(12)]) == 5.5


def test_alignment_detects_duplicates_and_unmatched_timestamps() -> None:
    result = validate_alignment(["a", "b", "b"], ["a", "c"])
    assert result == {"matched_timestamps": 1, "unmatched_left": 1, "unmatched_right": 1, "duplicate_left": 1, "duplicate_right": 0}


def test_canonical_schema_and_aggregates_exist() -> None:
    import pyarrow.parquet as pq
    table = pq.read_table(ROOT / "data/processed/research_hourly_index.parquet")
    assert table.num_rows == 8784
    assert table.column_names == ["timestamp", "actual_system_load", "day_ahead_system_load", "actual_wind", "day_ahead_wind", "actual_pv", "day_ahead_pv"]
    metadata = json.loads((ROOT / "data/processed/research_hourly_index.metadata.json").read_text())
    assert all(value["matched_timestamps"] == 8784 and not any(value[key] for key in ("unmatched_left", "unmatched_right", "duplicate_left", "duplicate_right")) for value in metadata["alignment"].values())
    assert metadata["source_checksums_before"] == metadata["source_checksums_after"]


def test_deterministic_rebuild_checksums() -> None:
    from smartgrid_mlops.data.pipeline import build_canonical_datasets
    first = build_canonical_datasets()
    second = build_canonical_datasets()
    assert first["outputs"] == second["outputs"]
    assert second["source_unchanged"]
