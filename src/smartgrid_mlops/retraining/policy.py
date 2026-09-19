from __future__ import annotations
import hashlib, json
from dataclasses import dataclass
from pathlib import Path
from smartgrid_mlops.mlops.fingerprints import fingerprint

IDENTITY_KEYS = (
    "policy_id", "policy_version", "severity_policy", "performance_signal_rule",
    "min_persistence_windows", "data_quality_policy", "label_availability_policy",
    "minimum_new_labeled_samples", "cooldown_hours", "cooldown_scope",
    "allowed_reference_states", "allowed_model_families", "allowed_feature_sets",
    "allowed_feature_set_id", "hyperparameter_policy", "feature_selection_policy",
    "seed_policy", "training_window_policy", "evaluation_policy",
    "challenger_registration_policy", "duplicate_request_policy", "job_policy",
    "final_test_constraints",
)


@dataclass(frozen=True)
class RetrainingPolicy:
    document: dict
    checksum: str
    retraining_policy_fingerprint: str

    @classmethod
    def load(cls, path: Path) -> "RetrainingPolicy":
        raw = Path(path).read_bytes()
        doc = json.loads(raw)
        checksum = hashlib.sha256(raw).hexdigest()
        identity = {key: doc.get(key, "UNKNOWN") for key in IDENTITY_KEYS}
        return cls(doc, checksum, fingerprint(identity, "retraining-policy-v1"))

    @property
    def policy_id(self): return self.document["policy_id"]
    @property
    def version(self): return self.document["policy_version"]
