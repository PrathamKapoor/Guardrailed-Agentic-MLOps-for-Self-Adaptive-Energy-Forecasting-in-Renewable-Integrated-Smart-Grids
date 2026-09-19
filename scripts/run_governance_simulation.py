"""Run frozen deterministic governance scenarios. No final-test option or data access exists."""
from __future__ import annotations
import argparse,csv,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from smartgrid_mlops.governance.audit import audit_decision
from smartgrid_mlops.governance.policies import GovernancePolicy
from smartgrid_mlops.governance.simulator import GovernanceSimulator,calculate_metrics
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

def run(selected,official):
 policy=GovernancePolicy.load(ROOT/"config/governance/phase_13_policy.yaml");sim=GovernanceSimulator(ROOT,policy);results=[];decisions=[];gates=[]
 for scenario in selected:
  decision=sim.execute(scenario);decisions.append(decision.to_dict());primary=decision.reason_codes[0]
  correct=decision.decision==scenario["expected_decision"] and primary==scenario["expected_reason"]
  results.append({"scenario":scenario["id"],"requested_transition":decision.requested_transition,"key_condition":scenario["fixture"]+str(scenario.get("mutation",{})),"expected_decision":scenario["expected_decision"],"actual_decision":decision.decision,"primary_reason":primary,"correct":correct,"safety_relevant":scenario["safety_relevant"],"unsafe_attempt":scenario["unsafe_attempt"]})
  for gate in decision.gate_results:gates.append({"scenario":scenario["id"],**gate})
  audit_decision(ROOT/"artifacts/mlops/audit/events.jsonl",decision,scenario["id"] if official else "NON_EVIDENCE_SMOKE")
 if official:
  out=ROOT/"artifacts/governance/phase_13";out.mkdir(parents=True,exist_ok=True)
  write("artifacts/governance/phase_13/decisions.jsonl","".join(json.dumps(x,sort_keys=True)+"\n" for x in decisions))
  for relative,rows in (("artifacts/governance/phase_13/scenario_results.csv",results),("artifacts/governance/phase_13/gate_results.csv",gates)):
   p=ROOT/relative
   with p.open("w",newline="",encoding="utf-8") as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
  metrics=calculate_metrics(results);dump("artifacts/governance/phase_13/simulation_manifest.yaml",{"phase":"13","status":"OFFICIAL_COMPLETE","tracking_origin":"NATIVE_DETERMINISTIC_GOVERNANCE","policy_checksum":policy.checksum,"governance_policy_fingerprint":policy.governance_policy_fingerprint,"scenario_freeze":"artifacts/experimental_design/phase_13_governance_scenarios.yaml","scenario_results":"artifacts/governance/phase_13/scenario_results.csv","decision_artifact":"artifacts/governance/phase_13/decisions.jsonl","metrics":metrics,"final_test_data_access":False,"phase_13_new_final_test_reads":0})
  write("artifacts/research_tables/governance_scenario_results.csv",(ROOT/"artifacts/governance/phase_13/scenario_results.csv").read_text())
  print(json.dumps(metrics,indent=2));return int(not all(x["correct"] for x in results))
 decision=decisions[0];dump("artifacts/governance/phase_13/non_evidence_smoke.yaml",{"evidence_status":"NON_EVIDENCE_SMOKE","decision":decision,"policy_loading":"PASS","state_validation":"PASS","decision_generation":"PASS","audit_event":"PASS","artifact_writing":"PASS","excluded_from_official_evidence":True,"final_test_data_access":False})
 print(json.dumps(decision,indent=2));return 0

def main():
 parser=argparse.ArgumentParser();group=parser.add_mutually_exclusive_group(required=True);group.add_argument("--smoke",action="store_true");group.add_argument("--all",action="store_true");group.add_argument("--scenario");args=parser.parse_args()
 frozen=read("artifacts/experimental_design/phase_13_governance_scenarios.yaml")["scenarios"]
 if args.smoke:return run([next(x for x in frozen if x["id"]=="G14")],False)
 if args.scenario:
  found=[x for x in frozen if x["id"]==args.scenario]
  if not found:parser.error("unknown frozen scenario")
  return run(found,False)
 return run(frozen,True)
if __name__=="__main__":raise SystemExit(main())
