from __future__ import annotations
import hashlib,json
from dataclasses import dataclass
from pathlib import Path
from smartgrid_mlops.mlops.fingerprints import fingerprint

@dataclass(frozen=True)
class GovernancePolicy:
    document: dict
    checksum: str
    governance_policy_fingerprint: str

    @classmethod
    def load(cls,path:Path):
        raw=path.read_bytes();doc=json.loads(raw);checksum=hashlib.sha256(raw).hexdigest()
        identity={key:doc[key] for key in ("policy_id","policy_version","required_evidence_statuses","required_lineage_status","required_reproducibility_metadata","accepted_protocol_hashes","fingerprint_requirements","benchmark_policy","statistical_evidence_policy","approval_policy","deviation_policy","transition_rules","rollback_requirements","final_test_constraints")}
        return cls(doc,checksum,fingerprint(identity,"governance-policy-v1"))
    @property
    def policy_id(self):return self.document["policy_id"]
    @property
    def version(self):return self.document["policy_version"]
