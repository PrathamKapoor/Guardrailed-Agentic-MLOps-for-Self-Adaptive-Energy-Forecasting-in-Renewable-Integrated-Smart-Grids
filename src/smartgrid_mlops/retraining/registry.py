"""Phase 15 challenger registry: additive file, never replacing prior freezes.

The Phase 13 lifecycle registry is intentionally NOT mutated here; challenger
registration in Phase 15 is a new registry file with REGISTERED_CHALLENGER
entries whose promotion_eligible is false by construction."""
from __future__ import annotations
import json
from pathlib import Path
from .challenger import ChallengerRecord

SCHEMA = "phase15-challenger-registry-v1"


class ChallengerRegistry:
    def __init__(self, document: dict | None = None):
        self.document = document or {"schema_version": SCHEMA, "policy_version": "15.0.0", "entries": []}

    @classmethod
    def load(cls, path: Path) -> "ChallengerRegistry":
        return cls(json.loads(Path(path).read_text(encoding="utf-8")) if Path(path).exists() else None)

    def find(self, challenger_id: str):
        return next((e for e in self.document["entries"] if e["challenger_id"] == challenger_id), None)

    def find_by_instance(self, model_instance_fingerprint: str):
        return next((e for e in self.document["entries"]
                     if e["model_instance_fingerprint"] == model_instance_fingerprint), None)

    def register(self, record: ChallengerRecord) -> dict:
        existing = self.find_by_instance(record.model_instance_fingerprint)
        if existing is not None:
            return existing
        entry = record.to_dict()
        self.document["entries"].append(entry)
        return entry

    @property
    def entries(self): return self.document["entries"]

    def dump(self, path: Path):
        path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.document, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def validate_no_promotion(self) -> bool:
        return all((e["registry_state"] == "REGISTERED_CHALLENGER" and e["promotion_eligible"] is False)
                   for e in self.document["entries"])
