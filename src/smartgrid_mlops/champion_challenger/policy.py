from __future__ import annotations
import hashlib, json
from dataclasses import dataclass
from pathlib import Path
from smartgrid_mlops.mlops.fingerprints import fingerprint

IDENTITY_KEYS = (
    "policy_id", "policy_version", "mode", "decision_values", "gate_order",
    "performance_policy", "benchmark_policy", "statistical_evidence_policy",
    "approval_policy", "canary_policy", "post_promotion_policy", "rollback_policy",
    "accepted_protocol_hashes", "unsafe_attempt_definition", "final_test_constraints",
)


@dataclass(frozen=True)
class PromotionPolicy:
    document: dict
    checksum: str
    promotion_policy_fingerprint: str

    @classmethod
    def load(cls, path: Path) -> "PromotionPolicy":
        raw = Path(path).read_bytes()
        doc = json.loads(raw)
        checksum = hashlib.sha256(raw).hexdigest()
        identity = {key: doc.get(key, "UNKNOWN") for key in IDENTITY_KEYS}
        return cls(doc, checksum, fingerprint(identity, "promotion-policy-v1"))

    @property
    def policy_id(self): return self.document["policy_id"]
    @property
    def version(self): return self.document["policy_version"]
