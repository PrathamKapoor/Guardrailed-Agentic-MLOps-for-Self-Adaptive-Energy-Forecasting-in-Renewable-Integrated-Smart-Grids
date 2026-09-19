"""Read-only RTS-GMLC audit runner and artifact writer."""

from __future__ import annotations

import csv
import json
import math
import struct
import zlib
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .csv_profile import profile_timeseries
from .generator_mapping import build_mapping
from .metadata_audit import profile_metadata, read_table
from .validation import source_checksums


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATASET_ROOT = PROJECT_ROOT / "data/external/RTS-GMLC"
AUDIT_ROOT = PROJECT_ROOT / "artifacts/data_audit"
CRITICAL = [
    "RTS_Data/SourceData/gen.csv", "RTS_Data/SourceData/bus.csv", "RTS_Data/SourceData/timeseries_pointers.csv",
    "RTS_Data/timeseries_data_files/Load/DAY_AHEAD_regional_Load.csv", "RTS_Data/timeseries_data_files/Load/REAL_TIME_regional_Load.csv",
    "RTS_Data/timeseries_data_files/WIND/DAY_AHEAD_wind.csv", "RTS_Data/timeseries_data_files/WIND/REAL_TIME_wind.csv",
    "RTS_Data/timeseries_data_files/PV/DAY_AHEAD_pv.csv", "RTS_Data/timeseries_data_files/PV/REAL_TIME_pv.csv",
]
FILES = {
    "load_day_ahead": ("Load/DAY_AHEAD_regional_Load.csv", "load", 60), "load_real_time": ("Load/REAL_TIME_regional_Load.csv", "load", 5),
    "wind_day_ahead": ("WIND/DAY_AHEAD_wind.csv", "wind", 60), "wind_real_time": ("WIND/REAL_TIME_wind.csv", "wind", 5),
    "pv_day_ahead": ("PV/DAY_AHEAD_pv.csv", "pv", 60), "pv_real_time": ("PV/REAL_TIME_pv.csv", "pv", 5),
    "rtpv_day_ahead": ("RTPV/DAY_AHEAD_rtpv.csv", "rtpv", 60), "rtpv_real_time": ("RTPV/REAL_TIME_rtpv.csv", "rtpv", 5),
}


def _write_png(path: Path, values: list[float], title: str, distribution: bool = False) -> None:
    """Minimal dependency-free PNG line/histogram plot for audit artifacts."""
    width, height = 900, 360
    pixels = bytearray([255, 255, 255] * width * height)
    def point(x: int, y: int, color: tuple[int, int, int]) -> None:
        if 0 <= x < width and 0 <= y < height:
            offset = (y * width + x) * 3; pixels[offset:offset + 3] = bytes(color)
    for x in range(50, width - 20): point(x, height - 35, (180, 180, 180))
    for y in range(20, height - 35): point(50, y, (180, 180, 180))
    if values:
        low, high = min(values), max(values)
        span = high - low or 1.0
        if distribution:
            bins = [0] * 40
            for value in values: bins[min(39, int((value - low) / span * 40))] += 1
            maximum = max(bins) or 1
            for index, count in enumerate(bins):
                left = 52 + index * (width - 75) // 40; right = 52 + (index + 1) * (width - 75) // 40
                top = height - 36 - int(count / maximum * (height - 65))
                for x in range(left, right):
                    for y in range(top, height - 35): point(x, y, (44, 116, 179))
        else:
            prior = None
            for index, value in enumerate(values):
                x = 51 + int(index * (width - 72) / max(1, len(values) - 1)); y = height - 36 - int((value - low) / span * (height - 65))
                if prior:
                    x0, y0 = prior; steps = max(abs(x - x0), abs(y - y0), 1)
                    for step in range(steps + 1): point(x0 + (x - x0) * step // steps, y0 + (y - y0) * step // steps, (22, 99, 68))
                prior = (x, y)
    raw = b"".join(b"\x00" + bytes(pixels[row * width * 3:(row + 1) * width * 3]) for row in range(height))
    def chunk(kind: bytes, payload: bytes) -> bytes: return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload) & 0xffffffff)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def _profile_row(profile: dict[str, Any]) -> dict[str, Any]:
    temporal = profile["temporal"]
    return {"relative_path": profile["relative_path"], "category": profile["category"], "resolution": f"{profile['resolution_minutes']}-minute", "rows": profile["rows"], "columns": profile["columns"], "missing_cells": profile["missing_cells"], "duplicate_rows": profile["duplicate_rows"], "negative_values": profile["negative_values"], "zero_values": profile["zero_values"], "min_period": temporal["period_range"][0], "max_period": temporal["period_range"][1], "min_year": temporal["year_range"][0], "max_year": temporal["year_range"][1], "audit_status": "PASS" if not (profile["missing_cells"] or profile["duplicate_rows"] or temporal["missing_intervals"] or temporal["duplicate_timestamps"]) else "REVIEW"}


def _issues(profiles: dict[str, dict[str, Any]], mapping: list[dict[str, str]]) -> list[dict[str, str]]:
    issues: list[dict[str, str]] = []
    for key, profile in profiles.items():
        aggregate = profile["aggregate"]
        for direction in ("largest_positive_ramp", "largest_negative_ramp"):
            ramp = profile[direction]
            issues.append({"issue_id": f"{key}-{direction}", "file": profile["relative_path"], "series": "aggregate", "timestamp": ramp["timestamp"] or "unknown", "issue_type": "POTENTIAL_OUTLIER_RAMP", "severity": "INFO", "value": str(ramp["value"]), "evidence": "Largest observed first difference; legitimate grid behavior is not classified as bad data.", "recommended_action": "Retain; review during later extreme-condition analysis."})
        if profile["category"] in {"pv", "rtpv"}:
            issues.append({"issue_id": f"{key}-zero-behavior", "file": profile["relative_path"], "series": "aggregate", "timestamp": "not_applicable", "issue_type": "EXPECTED_ZERO_BEHAVIOR", "severity": "INFO", "value": str(aggregate["zero_percentage"]), "evidence": "PV/RTPV zero output is expected during nighttime and is not missingness.", "recommended_action": "Do not impute or classify as missing solely because output is zero."})
    capacity = {(row["generator_id"], row["timeseries_file"]): float(row["capacity"]) for row in mapping if row["capacity"] not in {"unknown", "not_applicable"}}
    for profile in profiles.values():
        if profile["category"] not in {"wind", "pv", "rtpv"}: continue
        for series, stats in profile["series"].items():
            cap = capacity.get((series, profile["relative_path"]))
            if cap is not None and stats["max"] is not None and stats["max"] > cap:
                issues.append({"issue_id": f"capacity-{profile['relative_path'].replace('/', '-')}-{series}", "file": profile["relative_path"], "series": series, "timestamp": "not_localized_in_phase_2", "issue_type": "OBSERVED_GT_METADATA_CAPACITY", "severity": "WARNING", "value": str(stats["max"]), "evidence": f"observed maximum exceeds PMax MW {cap}; scaling-factor/parameter semantics require follow-up.", "recommended_action": "Investigate pointer scaling and source semantics; do not modify values."})
    return issues


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0]) if rows else []
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields); writer.writeheader(); writer.writerows(rows)


def run_audit(summary: bool = False) -> dict[str, Any]:
    before = source_checksums(DATASET_ROOT, CRITICAL)
    profiles = {}
    for key, (relative, category, minutes) in FILES.items():
        profile = profile_timeseries(DATASET_ROOT / "RTS_Data/timeseries_data_files" / relative, category, minutes, include_series_percentiles=(category == "load"))
        profile["relative_path"] = f"RTS_Data/timeseries_data_files/{relative}"
        profiles[key] = profile
    source = DATASET_ROOT / "RTS_Data/SourceData"
    metadata = {
        "gen": profile_metadata(source / "gen.csv", ["Unit Type", "Category", "Fuel", "Bus ID"]),
        "bus": profile_metadata(source / "bus.csv", ["Area", "Sub Area", "Zone", "Bus Type"]),
        "timeseries_pointers": profile_metadata(source / "timeseries_pointers.csv", ["Simulation", "Category", "Parameter", "Data File"]),
    }
    mapping = build_mapping(DATASET_ROOT, profiles)
    issues = _issues(profiles, mapping)
    after = source_checksums(DATASET_ROOT, CRITICAL)
    targets = [
        {"task": "System total electricity load", "priority": "PRIMARY", "actual_file": profiles["load_real_time"]["relative_path"], "baseline_file": profiles["load_day_ahead"]["relative_path"], "frequency": "5-minute actual aligned later to hourly baseline", "unit": "MW (documented pointer/metadata context)", "mapping_confidence": "VERIFIED", "notes": "Sum of three documented regional load columns; temporary audit aggregate only."},
        {"task": "Aggregate wind generation", "priority": "PRIMARY", "actual_file": profiles["wind_real_time"]["relative_path"], "baseline_file": profiles["wind_day_ahead"]["relative_path"], "frequency": "5-minute actual aligned later to hourly baseline", "unit": "MW parameter context", "mapping_confidence": "VERIFIED", "notes": "Four metadata-verified Wind generators."},
        {"task": "Aggregate utility-scale PV generation", "priority": "PRIMARY", "actual_file": profiles["pv_real_time"]["relative_path"], "baseline_file": profiles["pv_day_ahead"]["relative_path"], "frequency": "5-minute actual aligned later to hourly baseline", "unit": "MW parameter context", "mapping_confidence": "VERIFIED", "notes": "25 metadata-verified Solar PV generators; retain nighttime zeros."},
        {"task": "Regional load and plant-level wind/PV", "priority": "SECONDARY", "actual_file": "same resource files", "baseline_file": "same resource files", "frequency": "resource-native", "unit": "same as source", "mapping_confidence": "VERIFIED", "notes": "Useful disaggregated targets after canonical preprocessing."},
        {"task": "Aggregate rooftop PV", "priority": "SECONDARY", "actual_file": profiles["rtpv_real_time"]["relative_path"], "baseline_file": profiles["rtpv_day_ahead"]["relative_path"], "frequency": "resource-native", "unit": "MW parameter context", "mapping_confidence": "VERIFIED", "notes": "Keep separate from utility-scale PV; it is typically non-dispatchable in the source PCM context."},
        {"task": "CSP and Hydro", "priority": "OUT_OF_SCOPE", "actual_file": "available but not audited deeply", "baseline_file": "not selected", "frequency": "not selected", "unit": "not selected", "mapping_confidence": "not_applicable", "notes": "Present but outside initial demand/wind/solar task focus."},
    ]
    audit = {"dataset": {"id": "RTS-GMLC", "source_root": "data/external/RTS-GMLC", "audit_timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), "read_only": True}, "metadata": metadata, "load": {key: value for key, value in profiles.items() if key.startswith("load_")}, "wind": {key: value for key, value in profiles.items() if key.startswith("wind_")}, "pv": {key: value for key, value in profiles.items() if key.startswith("pv_")}, "rtpv": {key: value for key, value in profiles.items() if key.startswith("rtpv_")}, "timestamps": {key: value["temporal"] for key, value in profiles.items()}, "data_quality": {"issues": issues, "source_unchanged": before == after}, "generator_mapping": {"rows": mapping, "status_counts": dict(Counter(row["mapping_status"] for row in mapping))}, "forecasting_targets": targets, "recommended_hourly_aggregation": {"method": "mean", "confidence": "medium", "evidence": "The source calls the load series power demand and pointer/metadata parameters use MW; day-ahead is hourly and real-time is 5-minute. Mean preserves average power when later aligning resolutions.", "caveat": "The time-series README also uses available energy-generation wording for renewables; Phase 3 must preserve units and make the final contract explicit."}, "limitations": ["Single observed CSV year (2020).", "RTS-GMLC is a research/test system, not operating-utility measurements.", "No native raw meteorological observations are used in this experiment.", "Constructed/test-system characteristics may limit external generalization.", "One year cannot directly establish multi-year concept drift.", "DAY_AHEAD and REAL_TIME have different native resolutions.", "Bundled PDF date example differs from actual CSV year.", "Exact period interval-label semantics (start versus end label) are not explicit in inspected source documentation; audit reconstruction uses a start-of-interval convention solely for continuity checking."], "source_checksums_before": before, "source_checksums_after": after}
    if not summary:
        AUDIT_ROOT.mkdir(parents=True, exist_ok=True)
        (AUDIT_ROOT / "rts_gmlc_audit.json").write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
        _write_csv(AUDIT_ROOT / "file_profiles.csv", [_profile_row(profile) for profile in profiles.values()])
        _write_csv(AUDIT_ROOT / "data_quality_issues.csv", issues)
        _write_csv(AUDIT_ROOT / "generator_mapping.csv", mapping)
        for resource in ("load", "wind", "pv"):
            profile = profiles[f"{resource}_real_time"]
            values = [value for _, value in profile["aggregate_first_values"]]
            _write_png(AUDIT_ROOT / "plots" / f"{resource}_sample_week.png", values, resource)
            _write_png(AUDIT_ROOT / "plots" / f"{resource}_distribution.png", values, resource, distribution=True)
            _write_png(AUDIT_ROOT / "plots" / f"average_{resource}_by_hour.png", [value or 0.0 for value in profile["average_aggregate_by_hour"]], resource)
    return audit
