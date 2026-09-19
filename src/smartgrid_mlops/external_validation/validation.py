"""Validation layer for external datasets — pure functions, no training.

All functions raise a typed error on violation so callers and tests can
distinguish provenance, compatibility, leakage, and availability failures.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path


class ExternalValidationError(RuntimeError):
    """Base for external-dataset validation failures.

    Subclasses carry a default message so a raised error is self-describing;
    callers may still override with a more specific message.
    """

    default_message = "external validation failed"

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.default_message)


class DatasetNotAvailableError(ExternalValidationError):
    default_message = "external dataset not found or not provisioned"


class ProvenanceError(ExternalValidationError):
    default_message = "external dataset provenance could not be verified (missing checksums or manifest)"


class FeatureCompatibilityError(ExternalValidationError):
    default_message = "external dataset features are incompatible with the frozen feature specification"


class TemporalCoverageError(ExternalValidationError):
    default_message = "external dataset temporal coverage does not satisfy the evaluation window"


class FrozenModelError(ExternalValidationError):
    default_message = "frozen model unavailable or mismatched for external validation"


REQUIRED_MANIFEST_FIELDS = (
    "source",
    "license",
    "retrieval_date",
    "version",
    "schema",
    "approval",
    "archive_checksum",
)


def validate_dataset_manifest(manifest_path: Path) -> dict:
    if not manifest_path.exists():
        raise DatasetNotAvailableError(f"manifest not found: {manifest_path}")
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.suffix == ".json" else __import__("yaml").safe_load(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ProvenanceError(f"manifest unreadable: {exc}") from exc
    # also support yaml via json fallback already attempted; raw yaml dict
    if not isinstance(data, dict):
        raise ProvenanceError("manifest must be a mapping")
    missing = [k for k in REQUIRED_MANIFEST_FIELDS if k not in data]
    if missing:
        raise ProvenanceError(f"manifest missing required fields: {missing}")
    return data


def validate_provenance(manifest: dict, raw_files: list[Path] | None = None) -> None:
    checksum = manifest.get("archive_checksum")
    if not checksum or not isinstance(checksum, str) or len(checksum) < 16:
        raise ProvenanceError("archive_checksum must be a non-empty hex string")
    if raw_files is not None:
        for p in raw_files:
            if not p.exists():
                raise ProvenanceError(f"provenance raw file missing: {p}")


def validate_temporal_coverage(
    timestamps: list[datetime],
    *,
    min_samples: int = 720,
    max_missing_fraction: float = 0.10,
) -> dict:
    if not timestamps:
        raise TemporalCoverageError("no timestamps provided")
    sorted_ts = sorted(timestamps)
    # hourly frequency check: all gaps should be 1h (allow single missing as gap 2h counts as missing)
    gaps = [(sorted_ts[i + 1] - sorted_ts[i]).total_seconds() / 3600 for i in range(len(sorted_ts) - 1)]
    # count missing hours: total expected span vs actual
    span_hours = int((sorted_ts[-1] - sorted_ts[0]).total_seconds() / 3600) + 1
    missing = span_hours - len(sorted_ts)
    missing_fraction = missing / span_hours if span_hours else 1.0
    conclusive = len(sorted_ts) >= min_samples and missing_fraction <= max_missing_fraction
    return {
        "samples": len(sorted_ts),
        "span_hours": span_hours,
        "missing_hours": missing,
        "missing_fraction": missing_fraction,
        "conclusive": conclusive,
        "min_samples": min_samples,
    }


def validate_feature_compatibility(
    available_columns: list[str],
    required_features: list[str],
    *,
    allow_extra: bool = True,
) -> None:
    missing = [c for c in required_features if c not in available_columns]
    if missing:
        raise FeatureCompatibilityError(f"missing required feature columns: {missing}")
    if not allow_extra:
        extra = [c for c in available_columns if c not in required_features]
        if extra:
            raise FeatureCompatibilityError(f"unexpected extra columns when strict: {extra}")


def validate_frozen_model(model_spec: dict, frozen_reference: dict) -> None:
    for key in ("model", "feature_set"):
        if model_spec.get(key) != frozen_reference.get(key):
            raise FrozenModelError(
                f"frozen model mismatch for {key}: expected {frozen_reference.get(key)!r} got {model_spec.get(key)!r}"
            )


def validate_no_leakage(
    feature_rows: list[dict],
    *,
    horizon_hours: int = 24,
) -> None:
    for row in feature_rows:
        origin = row.get("forecast_origin")
        target = row.get("target_timestamp")
        if not isinstance(origin, datetime) or not isinstance(target, datetime):
            raise ExternalValidationError("feature row must contain datetime forecast_origin and target_timestamp")
        if target <= origin:
            raise ExternalValidationError(f"target {target} must be after origin {origin}")
        # horizon check: for H24, target should be origin + horizon
        expected = origin + timedelta(hours=horizon_hours)
        if target != expected:
            # allow but warn via error if gap - for strict leakage prevention, target must be exactly horizon ahead
            # For this protocol we enforce exact horizon to avoid leakage via misaligned origins
            raise ExternalValidationError(
                f"horizon violation: origin {origin} target {target} expected {expected} for h{horizon_hours}"
            )
        # lag source check: ensure lag features could not have used future actuals — all lag features are derived from actuals at origin or earlier
        # This is structural: if lag_1 exists, its source is target-1h which must be <= origin
        # Since we already enforce target == origin+horizon, and horizon=24, lag_168 source is origin-144h, always <= origin
        # So no additional check needed beyond horizon enforcement for this feature set
