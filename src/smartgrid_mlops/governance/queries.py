from __future__ import annotations
import json
from pathlib import Path

class GovernanceQueries:
    def __init__(self,root:Path):
        self.lifecycle=json.loads((root/"artifacts/model_registry/lifecycle_registry.yaml").read_text())["entries"]
        path=root/"artifacts/governance/phase_13/decisions.jsonl";self.decisions=[json.loads(x) for x in path.read_text().splitlines() if x.strip()] if path.exists() else []
    def get_model_lifecycle_state(self,registry_id):return next(x["lifecycle_state"] for x in self.lifecycle if x["registry_id"]==registry_id)
    def get_decision_history(self,registry_id):return [x for x in self.decisions if x["subject_id"]==registry_id]
    def get_last_governance_decision(self,registry_id):
        values=self.get_decision_history(registry_id);return values[-1] if values else None
    def get_failed_gates(self,decision_id):return next(x["failed_gates"] for x in self.decisions if x["decision_id"]==decision_id)
    def is_promotion_eligible(self,registry_id):return next(bool(x["promotion_eligible"]) for x in self.lifecycle if x["registry_id"]==registry_id)
    def explain_denial(self,decision_id):return next(x["explanation"] for x in self.decisions if x["decision_id"]==decision_id)
