# Canonical dataset construction

The version `rts_gmlc_processed_v1` contains `load_hourly.parquet`, `wind_hourly.parquet`, `pv_hourly.parquet`, and `research_hourly_index.parquet`. All contain 8,784 timestamps for leap-year 2020. Native five-minute source-resolution values are retained separately for the three primary resources.

For every target, hourly REAL_TIME means and DAY_AHEAD values have 8,784 matched timestamps, zero unmatched timestamps, and zero duplicates. This is a structural alignment validation, not forecast benchmarking. The index contains only high-level actual and day-ahead variables for descriptive research use.
