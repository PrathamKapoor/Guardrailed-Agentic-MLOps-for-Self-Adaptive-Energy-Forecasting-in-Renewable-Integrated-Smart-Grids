"""Evidence-based mappings from source metadata, pointers, and series headers."""

from __future__ import annotations

import csv
from pathlib import Path


RESOURCE_CATEGORY = {"wind": "Wind", "pv": "Solar PV", "rtpv": "Solar RTPV"}


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def build_mapping(root: Path, profiles: dict[str, dict]) -> list[dict[str, str]]:
    source = root / "RTS_Data" / "SourceData"
    generators = {row["GEN UID"]: row for row in _rows(source / "gen.csv")}
    buses = {row["Bus ID"]: row for row in _rows(source / "bus.csv")}
    pointers = _rows(source / "timeseries_pointers.csv")
    output: list[dict[str, str]] = []
    for key, profile in profiles.items():
        resource = profile["category"]
        simulation = "DAY_AHEAD" if "DAY_AHEAD" in profile["relative_path"] else "REAL_TIME"
        expected_category = RESOURCE_CATEGORY.get(resource)
        for identifier in profile["value_columns"]:
            if resource == "load":
                candidates = [row for row in pointers if row["Category"] == "Area" and row["Object"] == identifier and profile["relative_path"].lower().endswith(Path(row["Data File"]).name.lower())]
                output.append({"resource_type": "load", "generator_id": "not_applicable", "source_identifier": identifier, "bus_id": "not_applicable", "region": identifier, "capacity": "not_applicable", "timeseries_file": profile["relative_path"], "timeseries_column": identifier, "mapping_status": "VERIFIED" if candidates else "AMBIGUOUS", "evidence_source": "timeseries_pointers.csv + Load header", "notes": "Area identifier mapped from MW Load pointer."})
                continue
            generator = generators.get(identifier)
            bus = buses.get(generator.get("Bus ID", ""), {}) if generator else {}
            candidates = [row for row in pointers if row["Category"] == "Generator" and row["Object"] == identifier and profile["relative_path"].endswith(Path(row["Data File"]).name)]
            category_ok = generator and generator.get("Category") == expected_category
            status = "VERIFIED" if generator and candidates and category_ok else "PARTIAL" if generator else "NOT_MAPPED"
            output.append({"resource_type": resource, "generator_id": identifier if generator else "unknown", "source_identifier": identifier, "bus_id": generator.get("Bus ID", "unknown") if generator else "unknown", "region": bus.get("Area", "unknown") if bus else "unknown", "capacity": generator.get("PMax MW", "unknown") if generator else "unknown", "timeseries_file": profile["relative_path"], "timeseries_column": identifier, "mapping_status": status, "evidence_source": "gen.csv + bus.csv + timeseries_pointers.csv + time-series header", "notes": f"metadata_category={generator.get('Category', 'unknown') if generator else 'unknown'}; simulation={simulation}"})
    return output
