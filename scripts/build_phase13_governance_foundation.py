"""Freeze Phase 13 governance metadata and initialize lifecycle state; no data/model access."""
from __future__ import annotations
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from smartgrid_mlops.governance.policies import GovernancePolicy
import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stderr,
)
LOGGER = logging.getLogger(__name__)
def read(p):return json.loads((ROOT/p).read_text(encoding="utf-8"))
def write(p,s):p=ROOT/p;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s,encoding="utf-8")
def dump(p,o):write(p,json.dumps(o,indent=2)+"\n")
def sha(p):return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()

policy=GovernancePolicy.load(ROOT/"config/governance/phase_13_policy.yaml")
scenarios=read("artifacts/experimental_design/phase_13_governance_scenarios.yaml")
write("config/governance/phase_13_policy.sha256",policy.checksum+"\n")
write("artifacts/experimental_design/phase_13_governance_scenarios.sha256",sha("artifacts/experimental_design/phase_13_governance_scenarios.yaml")+"\n")
dump("artifacts/governance/phase_13/policy_snapshot.yaml",{**policy.document,"policy_checksum":policy.checksum,"governance_policy_fingerprint":policy.governance_policy_fingerprint})

protocol={"phase":"13","status":"FROZEN_BEFORE_OFFICIAL_SIMULATION","research_objective":"To design and validate a deterministic model-lifecycle governance engine that constrains state transitions using reproducibility, evidence validity, lineage, benchmark, statistical, approval, and safety policies before autonomous decision-making is introduced.","secondary_objective":"To quantify whether deterministic governance prevents invalid or unsafe lifecycle actions under controlled simulated scenarios.","state_definitions":sorted(policy.document["transition_rules"]),"transition_definitions":policy.document["transition_rules"],"policy_id":policy.policy_id,"policy_version":policy.version,"policy_checksum":policy.checksum,"governance_policy_fingerprint":policy.governance_policy_fingerprint,"scenario_set":"artifacts/experimental_design/phase_13_governance_scenarios.yaml","scenario_checksum":sha("artifacts/experimental_design/phase_13_governance_scenarios.yaml"),"decision_semantics":["ALLOW","DENY","REQUIRE_APPROVAL","NO_OP"],"approval_semantics":policy.document["approval_policy"],"benchmark_rules":policy.document["benchmark_policy"],"evidence_rules":{"official_status":"VALID","audit_only":"DENY","invalidated":"DENY"},"lineage_rules":{"required_status":"COMPLETE","required_chain":"dataset -> processed_dataset -> feature_dataset -> protocol -> model_spec -> evaluation/evidence -> registry_entry"},"fingerprint_rules":policy.document["fingerprint_requirements"],"deviation_rules":policy.document["deviation_policy"],"metrics":{"decision_correctness":"actual matches / total scenarios * 100","unsafe_transition_prevention_rate":"unsafe transitions correctly blocked / unsafe transition attempts * 100","false_allow":"ALLOW when expected DENY","false_deny":"DENY when expected ALLOW"},"final_test_non_access_policy":{"training_access":False,"hpo_access":False,"model_selection_access":False,"feature_selection_access":False,"performance_evaluation":False,"integrity_audit_activation":False,"historical_integrity_access":"P9-DEV-002 historical only","phase_13_new_final_test_reads":0}}
dump("artifacts/experimental_design/phase_13_governance_protocol_freeze.yaml",protocol);protocol_sha=sha("artifacts/experimental_design/phase_13_governance_protocol_freeze.yaml");write("artifacts/experimental_design/phase_13_governance_protocol_freeze.sha256",protocol_sha+"\n")

registry=read("artifacts/model_registry/mlops_research_registry.yaml");entries=[]
for item in registry["entries"]:
 role=item["research_role"]
 if role=="REFERENCE":state="REGISTERED_REFERENCE"
 elif role=="CHALLENGER":state="REGISTERED_CHALLENGER"
 elif role=="BASELINE_COMPARATOR":state="NOT_APPLICABLE_BASELINE"
 else:state="INVALIDATED"
 entries.append({"registry_id":item["registry_id"],"research_role":role,"registry_state":item["registry_state"],"lifecycle_state":state,"benchmark_gate":item["development_benchmark_gate"],"promotion_eligible":False,"approval_state":"NOT_REQUIRED","last_policy_decision":None,"policy_version":policy.version,"audit_refs":[],"phase_12_registry_ref":"artifacts/model_registry/mlops_research_registry.yaml"})
doc={"schema_version":"phase13-lifecycle-registry-v1","policy_id":policy.policy_id,"policy_version":policy.version,"policy_checksum":policy.checksum,"phase_12_registry_unchanged":True,"entries":entries}
dump("artifacts/model_registry/lifecycle_registry.yaml",doc);dump("artifacts/governance/phase_13/lifecycle_registry_snapshot.yaml",doc)
print(json.dumps({"policy_checksum":policy.checksum,"policy_fingerprint":policy.governance_policy_fingerprint,"protocol_sha256":protocol_sha,"scenario_count":len(scenarios["scenarios"]),"lifecycle_entries":len(entries)},indent=2))
