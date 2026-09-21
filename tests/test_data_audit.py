import csv
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from smartgrid_mlops.data_audit.csv_profile import profile_timeseries
from smartgrid_mlops.data_audit.timestamp_audit import continuity_summary, reconstruct_timestamp


def _series(path: Path, rows: list[list[str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        writer.writerow(["Year", "Month", "Day", "Period", "unit_1"])
        writer.writerows(rows)


def test_csv_profiler_counts_and_numeric_quality() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        path = Path(temporary) / "series.csv"
        _series(path, [["2020", "2", "29", "1", "0"], ["2020", "2", "29", "2", "-2"], ["2020", "2", "29", "3", "9"]])
        profile = profile_timeseries(path, "test", 60)
        assert profile["rows"] == 3 and profile["columns"] == 5
        assert profile["zero_values"] == 1 and profile["negative_values"] == 1
        assert profile["temporal"]["specific_date_period_counts"]["2020-02-29"] == 3


def test_timestamp_reconstruction_leap_year_and_boundaries() -> None:
    assert reconstruct_timestamp(2020, 2, 28, 24, 60).isoformat() == "2020-02-28T23:00:00"
    assert reconstruct_timestamp(2020, 2, 29, 1, 60).isoformat() == "2020-02-29T00:00:00"
    assert reconstruct_timestamp(2020, 3, 1, 1, 60).isoformat() == "2020-03-01T00:00:00"
    assert reconstruct_timestamp(2020, 12, 31, 288, 5).isoformat() == "2020-12-31T23:55:00"


def test_missing_and_duplicate_timestamp_detection() -> None:
    timestamps = [reconstruct_timestamp(2020, 1, 1, item, 60) for item in (1, 2, 2, 4)]
    result = continuity_summary(timestamps, 60)
    assert result["duplicate_timestamps"] == 1 and result["missing_intervals"] == 1 and result["out_of_order"]


def test_outlier_and_constant_column_signals_are_deterministic() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        path = Path(temporary) / "series.csv"
        _series(path, [["2020", "1", "1", str(period), str(value)] for period, value in enumerate((0, 0, 0, 100), 1)])
        profile = profile_timeseries(path, "test", 60)
        assert profile["series"]["unit_1"]["max"] == 100
        assert profile["largest_positive_ramp"]["value"] == 100


def test_forecasting_task_schema_and_source_immutability() -> None:
    source_dir = ROOT / "data/external/RTS-GMLC/RTS_Data/timeseries_data_files"
    if not source_dir.exists():
        import pytest
        pytest.skip("data/external/RTS-GMLC source files not present in this environment")
    from smartgrid_mlops.data_audit.reporting import run_audit
    audit = run_audit(summary=True)
    required = {"task", "priority", "actual_file", "baseline_file", "frequency", "unit", "mapping_confidence", "notes"}
    assert all(required <= target.keys() for target in audit["forecasting_targets"])
    assert audit["data_quality"]["source_unchanged"]
    assert audit["generator_mapping"]["status_counts"].get("VERIFIED", 0) > 0
