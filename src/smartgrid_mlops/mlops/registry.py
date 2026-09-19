from __future__ import annotations

import json
from pathlib import Path

from .schemas import BENCHMARK_GATES, REGISTRY_STATES, RESEARCH_ROLES


class RegistrationError(ValueError):
    """Raised when a model registration violates registry invariants."""

    default_message = "model registration rejected by registry invariants"

    def __init__(self, message: str | None = None) -> None:
        super().__init__(message or self.default_message)


class ResearchRegistry:
    REQUIRED = {"registry_id", "target", "horizon", "research_role", "registry_state", "model_family", "framework", "implementation_id", "model_spec_fingerprint", "feature_set_id", "feature_spec_fingerprint", "dataset_fingerprint", "protocol_hash", "development_primary_metric", "development_MAE", "strongest_benchmark", "benchmark_MAE", "development_benchmark_gate", "evidence_status", "selection_evidence", "deviation_references", "created_from_phase", "final_test_performance_status"}

    def __init__(self, entries=None): self.entries = list(entries or [])

    @classmethod
    def load(cls, path: Path): return cls(json.loads(path.read_text(encoding="utf-8"))["entries"])

    def register(self, entry: dict, *, expected_model_fingerprint: str | None = None,
                 feature_fingerprint_valid=True, dataset_lineage_complete=True,
                 protocol_recognized=True, reference_selection_exists=True):
        missing = self.REQUIRED - entry.keys()
        if missing: raise RegistrationError(f"Missing registry fields: {sorted(missing)}")
        if entry["registry_state"] not in REGISTRY_STATES or entry["research_role"] not in RESEARCH_ROLES or entry["development_benchmark_gate"] not in BENCHMARK_GATES:
            raise RegistrationError("Unsupported registry state, role, or benchmark gate")
        if entry["registry_state"] == "REGISTERED_REFERENCE":
            if entry["evidence_status"] != "VALID": raise RegistrationError("Reference evidence must be VALID")
            if expected_model_fingerprint != entry["model_spec_fingerprint"]: raise RegistrationError("FINGERPRINT_MISMATCH")
            if not all((feature_fingerprint_valid, dataset_lineage_complete, protocol_recognized, reference_selection_exists)):
                raise RegistrationError("Reference registration gate failed")
            if any(x.get("status") == "UNRESOLVED_EVIDENCE_IMPACT" for x in entry["deviation_references"]):
                raise RegistrationError("Unresolved evidence-impacting deviation")
        if any(x["registry_id"] == entry["registry_id"] for x in self.entries): raise RegistrationError("Duplicate registry_id")
        self.entries.append(dict(entry))
        return entry

    @staticmethod
    def promotion_eligible(entry: dict) -> bool:
        return entry.get("evidence_status") == "VALID" and entry.get("development_benchmark_gate") == "BENCHMARK_GATE_PASS"

    def validate_one_reference_per_target(self):
        refs = [x for x in self.entries if x["research_role"] == "REFERENCE"]
        targets = [x["target"] for x in refs]
        if len(targets) != len(set(targets)): raise RegistrationError("More than one reference per target")
        return True

    def dump(self, path: Path, metadata: dict | None = None):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"schema_version": "phase12-research-registry-v1", **(metadata or {}), "entries": self.entries}, indent=2) + "\n", encoding="utf-8")
