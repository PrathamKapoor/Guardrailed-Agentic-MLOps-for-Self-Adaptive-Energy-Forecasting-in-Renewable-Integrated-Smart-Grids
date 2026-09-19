"""Stable scientific identities; timestamps and paths are deliberately excluded."""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


def fingerprint(value: Any, prefix: str) -> str:
    return f"{prefix}:sha256:{hashlib.sha256(canonical_json(value).encode()).hexdigest()}"


def model_spec_fingerprint(spec: Mapping[str, Any]) -> str:
    fields = ("model_family", "framework", "implementation_id", "feature_specification",
              "hyperparameters", "scaling_policy", "training_policy", "horizon")
    return fingerprint({key: spec.get(key, "UNKNOWN") for key in fields}, "model-spec-v1")


def feature_spec_fingerprint(spec: Mapping[str, Any]) -> str:
    fields = ("feature_set_id", "feature_names", "transformations",
              "forecast_horizon_availability_contract", "logical_feature_identity")
    return fingerprint({key: spec.get(key, "UNKNOWN") for key in fields}, "feature-spec-v1")


def dataset_fingerprint(spec: Mapping[str, Any]) -> str:
    fields = ("raw_source_checksum_set", "processed_manifest_hash", "logical_feature_fingerprints")
    return fingerprint({key: spec.get(key, "UNKNOWN") for key in fields}, "dataset-v1")


def research_run_key(*, phase: str, target: str, horizon: int | str,
                     model_spec_fingerprint: str, feature_set: str,
                     fold: str = "UNKNOWN", seed: int | str = "UNKNOWN",
                     evaluation_role: str = "UNKNOWN") -> str:
    return fingerprint({"phase": str(phase), "target": target.lower(), "horizon": str(horizon),
                        "model_spec_fingerprint": model_spec_fingerprint, "feature_set": feature_set,
                        "fold": str(fold), "seed": str(seed), "evaluation_role": evaluation_role}, "research-run-v1")
