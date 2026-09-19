import pyarrow as pa
import pyarrow.parquet as pq
from pathlib import Path

from smartgrid_mlops.features.integrity import INTEGRITY_AUDIT, binary_sha256, logical_content_sha256, parquet_logical_content_sha256


def test_logical_hash_is_deterministic_and_ignores_schema_metadata():
    table = pa.table({"timestamp": ["2020-01-01", "2020-01-02"], "x": [1.0, 2.0]})
    with_metadata = table.replace_schema_metadata({b"writer": b"other-version"})
    assert logical_content_sha256(table) == logical_content_sha256(table)
    assert logical_content_sha256(table) == logical_content_sha256(with_metadata)


def test_logical_hash_detects_values_schema_and_column_order():
    table = pa.table({"timestamp": ["2020-01-01"], "x": [1.0]})
    assert logical_content_sha256(table) != logical_content_sha256(pa.table({"timestamp": ["2020-01-01"], "x": [2.0]}))
    assert logical_content_sha256(table) != logical_content_sha256(pa.table({"timestamp": ["2020-01-01"], "x": [1]}))
    assert logical_content_sha256(table) != logical_content_sha256(pa.table({"x": [1.0], "timestamp": ["2020-01-01"]}))


def test_binary_mismatch_does_not_silently_resolve_logical_identity(tmp_path):
    table = pa.table({"x": [1.0, 2.0]})
    original = tmp_path / "original.parquet"
    altered = tmp_path / "altered.parquet"
    pq.write_table(table, original, compression="zstd")
    pq.write_table(table.replace_schema_metadata({b"writer": b"different"}), altered, compression="zstd")
    assert parquet_logical_content_sha256(original) == parquet_logical_content_sha256(altered)
    # A provenance repair must inspect both values; it cannot merely replace a manifest hash.
    assert binary_sha256(original) != binary_sha256(altered)


def test_tiny_feature_like_dataset_has_deterministic_logical_identity():
    first = pa.table({"forecast_origin": ["2020-01-01"], "lag_24": [12.0], "target": [13.0]})
    second = pa.table({"forecast_origin": ["2020-01-01"], "lag_24": [12.0], "target": [13.0]})
    assert logical_content_sha256(first) == logical_content_sha256(second)


def test_integrity_audit_api_is_separate_from_modeling_workflows():
    source = (Path(__file__).parents[1] / "src/smartgrid_mlops/features/integrity.py").read_text()
    assert INTEGRITY_AUDIT == "INTEGRITY_AUDIT"
    assert "smartgrid_mlops.models" not in source
    assert ".fit(" not in source and ".predict(" not in source
