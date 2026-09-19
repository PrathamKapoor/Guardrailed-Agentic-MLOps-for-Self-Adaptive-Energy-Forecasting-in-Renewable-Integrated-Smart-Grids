"""Phase 16 champion registry: additive, simulation-scoped.

Records scenario-scoped promotion outcomes (PROMOTED / ACTIVE, ROLLED_BACK,
REJECTED) with explicit SIMULATION labels. The authoritative Phase 13 lifecycle
registry is never modified by Phase 16; promotion exists only in simulation."""
from __future__ import annotations
import json
from pathlib import Path

SCHEMA = "phase16-champion-registry-v1"


class ChampionRegistry:
    def __init__(self, document: dict | None = None):
        self.document = document or {"schema_version": SCHEMA, "policy_version": "16.0.0",
                                     "mode": "SIMULATION", "promotions": [], "rollbacks": [],
                                     "preserved_models": []}

    @classmethod
    def load(cls, path: Path) -> "ChampionRegistry":
        p = Path(path)
        return cls(json.loads(p.read_text(encoding="utf-8")) if p.exists() else None)

    def record_promotion(self, entry: dict) -> dict:
        if not any(p["challenger_id"] == entry["challenger_id"] and p.get("scenario") == entry.get("scenario")
                   for p in self.document["promotions"]):
            self.document["promotions"].append(entry)
        return entry

    def record_rollback(self, entry: dict) -> dict:
        self.document["rollbacks"].append(entry)
        return entry

    def record_preservation(self, entry: dict) -> dict:
        if not any(p["model_id"] == entry["model_id"] for p in self.document["preserved_models"]):
            self.document["preserved_models"].append(entry)
        return entry

    @property
    def active_models(self):
        """Simulation-scoped ACTIVE entries: the currently serving model per scenario stream."""
        active = {}
        for promotion in self.document["promotions"]:
            stream = promotion.get("scenario") or promotion["challenger_id"]
            active[stream] = promotion
        for rollback in self.document["rollbacks"]:
            if rollback["outcome"] == "ROLLBACK_COMPLETED":
                stream = rollback.get("scenario") or rollback["promoted_model_id"]
                active[stream] = {"challenger_id": rollback["previous_model_id"],
                                  "state": "ACTIVE (restored reference, SIMULATION)", "restored": True}
        return active

    def dump(self, path: Path):
        path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
