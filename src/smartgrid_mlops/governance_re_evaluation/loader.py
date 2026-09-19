"""Stage 14: Package loader for governance re-evaluation.

This module reads Stage 13 candidate packages under
`artifacts/v2/governance_candidate_packages/<candidate_id>/` and
verifies their integrity.

The loader is a thin I/O layer. It does NOT interpret the evidence;
it does NOT construct governance objects; it does NOT call the
engine. It only loads files and validates checksums.

The loader is read-only with respect to the v1 tree and to the
Stage 13 packages.
"""
from __future__ import annotations
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Required files for every candidate package.
REQUIRED_FILES: tuple[str, ...] = (
    "candidate_manifest.json",
    "model_spec.json",
    "feature_spec.json",
    "data_split_manifest.json",
    "benchmark_evaluation.json",
    "protocol_compatibility.json",
    "reproducibility_manifest.json",
    "checksums.json",
)

STAGE_13_ROOT = Path(__file__).resolve().parents[3] / "artifacts" / "v2" / "governance_candidate_packages"
V2_ROOT = Path(__file__).resolve().parents[3] / "artifacts" / "v2" / "governance_re_evaluation"


@dataclass(frozen=True)
class LoadedPackage:
    """A Stage 13 candidate package, loaded and integrity-checked.

    The `package_dir` is the directory under
    `artifacts/v2/governance_candidate_packages/<candidate_id>/`.
    The `files` dict holds the parsed JSON content of every required
    file. The `integrity_ok` field records whether the per-file
    SHA-256s verified against the recorded checksums.json.
    """
    candidate_id: str
    package_dir: Path
    files: dict[str, dict] = field(default_factory=dict)
    integrity_ok: bool = False
    integrity_error: str = ""

    def file(self, name: str) -> dict:
        if name not in self.files:
            raise KeyError(
                f"package {self.candidate_id}: file {name!r} not loaded")
        return self.files[name]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def list_candidate_ids(packages_root: Path = STAGE_13_ROOT) -> list[str]:
    """List every candidate id that has a Stage 13 package on disk.

    Returns the sorted list of directory names under `packages_root`,
    excluding any non-directory entries (e.g. .gitkeep, manifest.json).
    """
    if not packages_root.exists():
        return []
    out: list[str] = []
    for entry in sorted(packages_root.iterdir()):
        if entry.is_dir() and (entry / "checksums.json").is_file():
            out.append(entry.name)
    return out


def load_package(candidate_id: str,
                  packages_root: Path = STAGE_13_ROOT) -> LoadedPackage:
    """Load a single Stage 13 candidate package. Verifies that all
    required files exist and that the per-file SHA-256s in
    `checksums.json` match the actual file contents. Returns a
    `LoadedPackage` with `integrity_ok=True` on success; raises
    `PackageIntegrityError` if a file is missing or a checksum
    mismatches.
    """
    pkg_dir = packages_root / candidate_id
    if not pkg_dir.is_dir():
        raise PackageIntegrityError(
            f"package directory missing: {pkg_dir}")
    files: dict[str, dict] = {}
    for fn in REQUIRED_FILES:
        p = pkg_dir / fn
        if not p.is_file():
            raise PackageIntegrityError(
                f"package {candidate_id}: required file missing: {fn}")
        try:
            files[fn] = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise PackageIntegrityError(
                f"package {candidate_id}: invalid JSON in {fn}: {e}")
    cs = files["checksums.json"]
    recorded = cs.get("file_hashes_sha256", {})
    actual_hashes: dict[str, str] = {}
    for fn in REQUIRED_FILES:
        if fn == "checksums.json":
            continue
        actual = _sha(pkg_dir / fn)
        actual_hashes[fn] = actual
        if fn not in recorded:
            raise PackageIntegrityError(
                f"package {candidate_id}: {fn} missing from checksums.json")
        if recorded[fn] != actual:
            raise PackageIntegrityError(
                f"package {candidate_id}: checksum mismatch for {fn}: "
                f"recorded={recorded[fn]}, actual={actual}")
    # Aggregate check: sha256 of sorted (filename, sha256) pairs.
    sorted_pairs = json.dumps(
        sorted(actual_hashes.items()),
        sort_keys=True, separators=(",", ":"))
    expected_agg = hashlib.sha256(sorted_pairs.encode()).hexdigest()
    if cs.get("aggregate_package_sha256") != expected_agg:
        raise PackageIntegrityError(
            f"package {candidate_id}: aggregate checksum mismatch: "
            f"recorded={cs.get('aggregate_package_sha256')}, "
            f"expected={expected_agg}")
    return LoadedPackage(
        candidate_id=candidate_id,
        package_dir=pkg_dir,
        files=files,
        integrity_ok=True,
    )


def load_all_packages(packages_root: Path = STAGE_13_ROOT) -> list[LoadedPackage]:
    """Load every Stage 13 candidate package on disk. Returns a list
    in stable (sorted) order."""
    out: list[LoadedPackage] = []
    for cid in list_candidate_ids(packages_root):
        out.append(load_package(cid, packages_root))
    return out


class PackageIntegrityError(RuntimeError):
    """Raised when a Stage 13 candidate package fails integrity
    checks (missing file, JSON parse error, or checksum mismatch).
    Stage 14 reports this honestly as an EVIDENCE_GAP and does NOT
    silently substitute or fabricate fingerprints."""
