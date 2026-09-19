#!/usr/bin/env python3
"""Safely acquire, validate, inventory, and verify the RTS-GMLC source dataset.

This Phase 1 utility intentionally performs no preprocessing or forecasting work.
It uses only the Python standard library so it can run in the base project setup.
"""
from __future__ import annotations

import os

try:
    from _scriptlog import get_logger  # scripts/_scriptlog.py: stdout logging, SMARTGRID_MLOPS_LOG_LEVEL
except ModuleNotFoundError:
    # Fallback for contexts where scripts/ is not importable (e.g. tests that
    # load this file by path): mirror the _scriptlog contract with stdlib.
    import logging as _logging

    def get_logger(name: str) -> "_logging.Logger":
        _logger = _logging.getLogger(f"smartgrid_mlops.scripts.{name}")
        if not _logger.handlers:
            import sys as _sys
            _handler = _logging.StreamHandler(_sys.stdout)
            _handler.setFormatter(_logging.Formatter("%(message)s"))
            _logger.addHandler(_handler)
            _logger.setLevel(os.environ.get("SMARTGRID_MLOPS_LOG_LEVEL", "INFO").upper())
            _logger.propagate = False
        return _logger

log = get_logger('bootstrap_rts_gmlc')


import argparse
import csv
import hashlib
import json
import os
import shutil
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET_ROOT = PROJECT_ROOT / "data" / "external" / "RTS-GMLC"
MANIFEST_PATH = PROJECT_ROOT / "data" / "manifests" / "rts_gmlc_manifest.yaml"
CHECKSUM_PATH = PROJECT_ROOT / "data" / "manifests" / "rts_gmlc_checksums.sha256"
OFFICIAL_REPOSITORY = "https://github.com/GridMod/RTS-GMLC"

REQUIRED_PATHS = (
    "README.md",
    "RTS_Data/SourceData/gen.csv",
    "RTS_Data/SourceData/bus.csv",
    "RTS_Data/SourceData/timeseries_pointers.csv",
    "RTS_Data/timeseries_data_files/Load",
)
RECOMMENDED_DIRECTORIES = ("Load", "WIND", "PV", "RTPV")
OPTIONAL_DIRECTORIES = ("CSP", "Hydro")
SOURCE_CSVS = ("gen.csv", "bus.csv", "timeseries_pointers.csv")


class DatasetValidationError(RuntimeError):
    """Raised when an archive or installed dataset is not a usable RTS-GMLC tree."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def is_safe_zip_member(name: str) -> bool:
    """Return whether a ZIP member remains below its extraction destination."""
    member = PurePosixPath(name)
    return not member.is_absolute() and ".." not in member.parts and not name.startswith(("/", "\\"))


def validate_zip(archive: Path) -> list[str]:
    """CRC-test an archive and reject traversal entries before extraction."""
    if not archive.is_file() or not zipfile.is_zipfile(archive):
        raise DatasetValidationError(f"Not a readable ZIP archive: {archive}")
    with zipfile.ZipFile(archive) as zipped:
        unsafe = [entry.filename for entry in zipped.infolist() if not is_safe_zip_member(entry.filename)]
        if unsafe:
            raise DatasetValidationError(f"Unsafe ZIP member(s): {unsafe[:3]}")
        corrupted = zipped.testzip()
        if corrupted:
            raise DatasetValidationError(f"ZIP CRC validation failed at: {corrupted}")
        names = zipped.namelist()
    if not any("RTS-GMLC" in name.upper() for name in names):
        raise DatasetValidationError("Archive contents do not identify RTS-GMLC")
    return names


def find_archive(search_root: Path) -> Path | None:
    """Find the preferred local RTS-GMLC archive without scanning beyond the workspace."""
    candidates: list[Path] = []
    for pattern in ("*RTS-GMLC*.zip", "*rts-gmlc*.zip", "*RTS_GMLC*.zip", "*rts_gmlc*.zip"):
        candidates.extend(search_root.glob(pattern))
        candidates.extend(search_root.glob(f"*/{pattern}"))
        candidates.extend(search_root.glob(f"*/*/{pattern}"))
    valid = sorted({candidate.resolve() for candidate in candidates if candidate.is_file()})
    return valid[0] if valid else None


def validate_structure(root: Path) -> dict[str, Any]:
    missing = [item for item in REQUIRED_PATHS if not (root / item).exists()]
    if missing:
        raise DatasetValidationError(f"RTS-GMLC required structure missing: {missing}")
    timeseries_root = root / "RTS_Data" / "timeseries_data_files"
    resources = {name.lower(): (timeseries_root / name).is_dir() for name in RECOMMENDED_DIRECTORIES}
    optional = {name.lower(): (timeseries_root / name).is_dir() for name in OPTIONAL_DIRECTORIES}
    if not all(resources.values()):
        raise DatasetValidationError(f"RTS-GMLC recommended forecasting resources missing: {resources}")
    return {"required": "PASS", "recommended_resources": resources, "optional_resources": optional}


def top_level_root(names: list[str]) -> str:
    roots = {PurePosixPath(name).parts[0] for name in names if PurePosixPath(name).parts}
    if len(roots) != 1:
        raise DatasetValidationError("Archive must contain one top-level directory")
    return roots.pop()


def extract_archive(archive: Path, destination: Path) -> None:
    names = validate_zip(archive)
    source_root = top_level_root(names)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="rts_gmlc_extract_", dir=destination.parent) as temporary:
        staging = Path(temporary)
        with zipfile.ZipFile(archive) as zipped:
            for info in zipped.infolist():
                target = staging / PurePosixPath(info.filename)
                target_parent = target.parent.resolve()
                if os.path.commonpath((str(staging.resolve()), str(target_parent))) != str(staging.resolve()):
                    raise DatasetValidationError(f"Unsafe ZIP extraction target: {info.filename}")
                if info.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with zipped.open(info) as source, target.open("wb") as output:
                        shutil.copyfileobj(source, output)
        extracted_root = staging / source_root
        validate_structure(extracted_root)
        shutil.move(str(extracted_root), str(destination))


def discover_key_files(root: Path) -> dict[str, list[str]]:
    source = root / "RTS_Data" / "SourceData"
    time_series = root / "RTS_Data" / "timeseries_data_files"
    relative = lambda path: path.relative_to(root).as_posix()
    return {
        "load": [relative(path) for path in sorted((time_series / "Load").glob("*.csv"))],
        "wind": [relative(path) for path in sorted((time_series / "WIND").glob("*.csv"))],
        "pv": [relative(path) for path in sorted((time_series / "PV").glob("*.csv"))],
        "rtpv": [relative(path) for path in sorted((time_series / "RTPV").glob("*.csv"))],
        "metadata": [relative(source / filename) for filename in SOURCE_CSVS],
    }


def inspect_csv(path: Path, root: Path) -> dict[str, Any]:
    """Capture structural facts only; no values are transformed or interpreted."""
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream)
        header = next(reader, [])
        first_row: list[str] | None = None
        last_row: list[str] | None = None
        row_count = 0
        ranges: dict[str, set[str]] = {key: set() for key in ("Year", "Month", "Day", "Period") if key in header}
        for row in reader:
            if not row:
                continue
            row_count += 1
            first_row = first_row or row
            last_row = row
            for key, values in ranges.items():
                index = header.index(key)
                if index < len(row):
                    values.add(row[index])
    result: dict[str, Any] = {
        "relative_path": path.relative_to(root).as_posix(),
        "file_size_bytes": path.stat().st_size,
        "row_count_excluding_header": row_count,
        "column_count": len(header),
        "column_names": header,
        "first_row": first_row,
        "last_row": last_row,
    }
    if ranges:
        result["temporal_ranges"] = {key.lower(): sorted(values, key=lambda value: int(value) if value.isdigit() else value) for key, values in ranges.items()}
    return result


def checksum_targets(root: Path, archive: Path | None = None) -> list[tuple[str, Path]]:
    key_files = discover_key_files(root)
    targets: list[tuple[str, Path]] = []
    if archive:
        targets.append((f"archive/{archive.name}", archive))
    for group in ("metadata", "load", "wind", "pv", "rtpv"):
        for relative in key_files[group]:
            targets.append((f"data/external/RTS-GMLC/{relative}", root / relative))
    return targets


def write_checksums(root: Path, archive: Path | None) -> dict[str, str]:
    CHECKSUM_PATH.parent.mkdir(parents=True, exist_ok=True)
    records = {relative: sha256_file(path) for relative, path in checksum_targets(root, archive)}
    CHECKSUM_PATH.write_text("".join(f"{digest}  {relative}\n" for relative, digest in records.items()), encoding="utf-8")
    return records


def verify_checksums(root: Path) -> bool:
    if not CHECKSUM_PATH.is_file():
        return False
    for line in CHECKSUM_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, relative = line.split("  ", 1)
        if relative.startswith("archive/"):
            continue  # The external archive is not copied into the project.
        path = PROJECT_ROOT / relative
        if not path.is_file() or sha256_file(path) != digest:
            return False
    return True


def archive_commit(archive: Path) -> str:
    """Use a GitHub ZIP's commit comment only when it is a full SHA-1 value."""
    with zipfile.ZipFile(archive) as zipped:
        comment = zipped.comment.decode("ascii", errors="ignore").strip()
    return comment if len(comment) == 40 and all(character in "0123456789abcdef" for character in comment.lower()) else "unknown"


def inferred_resolution(inspections: dict[str, dict[str, Any]]) -> tuple[str, str]:
    years = sorted({year for item in inspections.values() for year in item.get("temporal_ranges", {}).get("year", [])})
    resolutions: set[str] = set()
    for item in inspections.values():
        periods = item.get("temporal_ranges", {}).get("period", [])
        if periods and max(map(int, periods)) == 24 and item["row_count_excluding_header"] == 8784:
            resolutions.add("hourly")
        elif periods and max(map(int, periods)) == 288 and item["row_count_excluding_header"] == 105408:
            resolutions.add("5-minute")
        else:
            resolutions.add("not_verified")
    return (", ".join(years) if years else "not_verified", ", ".join(sorted(resolutions)))


def write_manifest(root: Path, archive: Path, archive_checksum: str, structure: dict[str, Any]) -> None:
    key_files = discover_key_files(root)
    inspections = {}
    for group_files in key_files.values():
        for relative in group_files:
            inspections[relative] = inspect_csv(root / relative, root)
    dataset_year, _ = inferred_resolution(inspections)
    resolutions = {}
    for relative, inspection in inspections.items():
        _, resolution = inferred_resolution({relative: inspection})
        resolutions[relative] = resolution
    manifest = {
        "dataset_id": "RTS-GMLC",
        "dataset_name": "Reliability Test System, Grid Modernization Lab Consortium",
        "provider": "Grid Modernization Lab Consortium (GridMod)",
        "official_repository": OFFICIAL_REPOSITORY,
        "acquisition_method": "ZIP",
        "acquisition_date": datetime.now(timezone.utc).date().isoformat(),
        "acquisition_archive": str(archive),
        "archive_checksum": archive_checksum,
        "repository_commit": archive_commit(archive),
        "dataset_root": "data/external/RTS-GMLC",
        "dataset_year": dataset_year,
        "time_resolutions": resolutions,
        "license": "NREL data use disclaimer in source repository README.md",
        "reproduction_status": "research/test system; not a reproduction claim",
        "key_files": key_files,
        "integrity": {"validated": True, "checksum_algorithm": "SHA-256", "validation_timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"), "structure": structure},
        "csv_structure": inspections,
        "notes": [
            "Source files are immutable in data/external/RTS-GMLC.",
            "CSV row counts exclude the header row.",
            "Time-resolution and semantic interpretation are documented separately after reading repository documentation.",
        ],
    }
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    # JSON is valid YAML 1.2 and avoids an undeclared PyYAML dependency.
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def verify_manifest() -> bool:
    if not MANIFEST_PATH.is_file():
        return False
    try:
        data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    required_fields = {"dataset_id", "dataset_name", "provider", "official_repository", "acquisition_method", "dataset_root", "key_files", "integrity"}
    return required_fields.issubset(data) and data["dataset_id"] == "RTS-GMLC"


def status(root: Path, acquisition_method: str) -> int:
    try:
        structure = validate_structure(root)
        integrity = "PASS"
    except DatasetValidationError:
        structure = {"recommended_resources": {}}
        integrity = "FAIL"
    key_files = discover_key_files(root) if integrity == "PASS" else {}
    checksums = "PASS" if integrity == "PASS" and verify_checksums(root) else "FAIL"
    manifest = "PASS" if verify_manifest() else "FAIL"
    log.info('RTS-GMLC Dataset Status\n')
    log.info(f"Dataset found: {('YES' if root.is_dir() else 'NO')}")
    log.info(f'Integrity: {integrity}')
    log.info(f'Manifest: {manifest}')
    log.info(f'Checksums: {checksums}\n')
    for resource in ("load", "wind", "pv", "rtpv"):
        log.info(f"{resource.upper()} data: {('FOUND' if key_files.get(resource) else 'MISSING')}")
    log.info(f"\nSource metadata: {('FOUND' if key_files.get('metadata') else 'MISSING')}")
    log.info(f'Acquisition method: {acquisition_method}')
    log.info(f'Dataset location: {root}')
    return 0 if integrity == checksums == manifest == "PASS" else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-only", action="store_true", help="Validate the installed dataset without extracting or writing files.")
    parser.add_argument("--archive", type=Path, help="Explicit RTS-GMLC ZIP archive path (for controlled use and tests).")
    args = parser.parse_args(argv)

    if args.verify_only:
        return status(DATASET_ROOT, "ZIP")
    if DATASET_ROOT.exists():
        try:
            validate_structure(DATASET_ROOT)
        except DatasetValidationError as error:
            log.error(f"Existing destination is invalid; it will not be overwritten: {error}")
            return 1
        log.info(f'Valid RTS-GMLC dataset already present; no extraction performed: {DATASET_ROOT}')
        return status(DATASET_ROOT, "ZIP")
    archive = args.archive.resolve() if args.archive else find_archive(PROJECT_ROOT.parent)
    if archive is None:
        log.error("No valid local RTS-GMLC ZIP found. Use the official fallback: git clone https://github.com/GridMod/RTS-GMLC.git data/external/RTS-GMLC")
        return 2
    try:
        validate_zip(archive)
        archive_checksum = sha256_file(archive)
        extract_archive(archive, DATASET_ROOT)
        structure = validate_structure(DATASET_ROOT)
        write_checksums(DATASET_ROOT, archive)
        write_manifest(DATASET_ROOT, archive, archive_checksum, structure)
    except (DatasetValidationError, OSError, zipfile.BadZipFile) as error:
        log.error(f"RTS-GMLC bootstrap failed: {error}")
        return 1
    return status(DATASET_ROOT, "ZIP")


if __name__ == "__main__":
    raise SystemExit(main())
