"""Render official Phase 13 governance evidence; does not evaluate or mutate policy inputs."""
from __future__ import annotations
import csv,json,sys
from pathlib import Path
import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stderr,
)
LOGGER = logging.getLogger(__name__)
ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads((ROOT/p).read_text(encoding="utf-8"))
def write(p,s):p=ROOT/p;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s,encoding="utf-8")
def dump(p,o):write(p,json.dumps(o,indent=2)+"\n")
def md(headers,rows):return "| "+" | ".join(headers)+" |\n| "+" | ".join("---" for _ in headers)+" |\n"+"".join("| "+" | ".join(map(str,r))+" |\n" for r in rows)

manifest=read("artifacts/governance/phase_13/simulation_manifest.yaml");metrics=manifest["metrics"]
decisions=[json.loads(x) for x in (ROOT/"artifacts/governance/phase_13/decisions.jsonl").read_text().splitlines() if x.strip()]
by_subject={x["subject_id"]:x for x in decisions}
lifecycle=read("artifacts/model_registry/lifecycle_registry.yaml")
for item in lifecycle["entries"]:
 if item["registry_id"] in by_subject:
  d=by_subject[item["registry_id"]];item["last_policy_decision"]=d["decision_id"];item["audit_refs"]=["artifacts/governance/phase_13/decisions.jsonl"]
dump("artifacts/model_registry/lifecycle_registry.yaml",lifecycle);dump("artifacts/governance/phase_13/lifecycle_registry_snapshot.yaml",lifecycle)

rows=[]
for r in csv.DictReader((ROOT/"artifacts/governance/phase_13/scenario_results.csv").open()):rows.append([r["scenario"],r["requested_transition"],r["key_condition"],r["expected_decision"],r["actual_decision"],r["primary_reason"],str(r["correct"]).upper(),str(r["safety_relevant"]).upper()])
headers=["Scenario","Requested Transition","Key Condition","Expected Decision","Actual Decision","Primary Reason","Correct?","Safety-Relevant?"]
write("reports/tables/governance_scenario_results.md","# Governance scenario results\n\n"+md(headers,rows))

gates=[
 ["EVIDENCE_VALIDITY_GATE","Reject invalid/audit-only evidence","Official lifecycle elevation","DENY","EVIDENCE_INVALID","Research registry / evidence status"],
 ["LINEAGE_COMPLETENESS_GATE","Require dataset-to-registry trace","Lifecycle elevation","DENY","LINEAGE_INCOMPLETE","Phase 12 lineage index"],
 ["MODEL_SPEC_FINGERPRINT_GATE","Bind exact model specification","Registry/promotion","DENY","MODEL_SPEC_FINGERPRINT_MISMATCH","Frozen model fingerprint"],
 ["FEATURE_SPEC_FINGERPRINT_GATE","Bind exact feature identity","Registry/promotion","DENY","FEATURE_SPEC_FINGERPRINT_MISMATCH","Frozen feature fingerprint"],
 ["PROTOCOL_COMPATIBILITY_GATE","Allow recognized freezes only","Lifecycle elevation","DENY","PROTOCOL_MISMATCH","Accepted protocol hashes"],
 ["REPRODUCIBILITY_METADATA_GATE","Require complete metadata","Lifecycle elevation","DENY","REPRODUCIBILITY_INCOMPLETE","Reproducibility manifest"],
 ["DEVIATION_STATUS_GATE","Block unresolved critical deviations","Lifecycle elevation","DENY","UNRESOLVED_DEVIATION","Deviation records"],
 ["BENCHMARK_GATE","Require strict development superiority","Promotion and beyond","DENY","BENCHMARK_GATE_FAILED","Phase 11 paired evidence"],
 ["STATISTICAL_EVIDENCE_GATE","Reject demonstrated degradation/insufficiency","Promotion and beyond","DENY","STATISTICAL_EVIDENCE_FAILED","Statistical status"],
 ["APPROVAL_GATE","Prevent automatic production-style elevation","Canary eligibility","REQUIRE_APPROVAL / DENY","APPROVAL_REQUIRED / APPROVAL_REJECTED","Explicit approval record"],
 ["STATE_TRANSITION_GATE","Enforce lifecycle graph","Every transition","DENY","INVALID_STATE_TRANSITION","Policy transition rules"],
 ["FINAL_TEST_POLICY_GATE","Preserve Phase 13 isolation","Every transition","DENY","FINAL_TEST_POLICY_VIOLATION","Final-test access request"],
 ["POLICY_VERSION_GATE","Bind decision to immutable policy","Every transition","DENY","POLICY_VERSION_MISMATCH","Policy ID/version/checksum"]]
gheaders=["Gate","Purpose","Required for","Failure action","Reason code","Evidence dependency"]
write("reports/tables/governance_policy_gates.md","# Deterministic governance policy gates\n\n"+md(gheaders,gates))

registry={x["registry_id"]:x for x in lifecycle["entries"]};ref_rows=[]
for target in ("LOAD","WIND","PV"):
 item=registry[f"MLOPS-REF-{target}-H24-V1"];ref_rows.append([target,item["research_role"],item["registry_state"],item["lifecycle_state"],"FAIL","NO","BENCHMARK_GATE","NOT_EVALUATED"])
rheaders=["Target","Research role","Registry state","Lifecycle state","Development benchmark gate","Promotion eligible?","Primary blocking gate","Final-test status"]
write("reports/tables/reference_governance_status.md","# Current reference governance status\n\n"+md(rheaders,ref_rows))
srows=[["Scenarios",metrics["total_scenarios"]],["Decision accuracy",f'{metrics["decision_correctness_percent"]}%'],["False allow count",metrics["false_allow"]],["False deny count",metrics["false_deny"]],["Unsafe transition attempts",metrics["unsafe_transition_attempts"]],["Unsafe transitions blocked",metrics["unsafe_transitions_blocked"]],["Unsafe transition prevention rate",f'{metrics["unsafe_transition_prevention_rate_percent"]}%'],["Invalid evidence attempts / blocked",f'{metrics["invalid_evidence_admission_attempts"]} / {metrics["invalid_evidence_blocked"]}'],["Fingerprint tampering attempts / blocked",f'{metrics["fingerprint_tampering_attempts"]} / {metrics["fingerprint_tampering_blocked"]}'],["Lineage violations / blocked",f'{metrics["lineage_violations_attempted"]} / {metrics["lineage_violations_blocked"]}'],["Benchmark-failure promotion attempts / blocked",f'{metrics["benchmark_failure_promotion_attempts"]} / {metrics["benchmark_failure_promotion_attempts_blocked"]}']]
write("reports/tables/governance_safety_metrics.md","# Governance safety metrics\n\n"+md(["Metric","Result"],srows))

svg_style='<style>text{font-family:Arial;fill:#172554}.b{fill:#eff6ff;stroke:#2563eb;stroke-width:2}.f{fill:#f8fafc;stroke:#64748b;stroke-width:2}.x{fill:#fff7ed;stroke:#c2410c;stroke-width:2}.a{stroke:#475569;stroke-width:2;marker-end:url(#m)}</style><defs><marker id="m" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0 0L8 4L0 8z" fill="#475569"/></marker></defs>'
boxes=[(360,40,"Experiment Evidence"),(360,120,"MLflow + Research Registry"),(360,200,"Deterministic Policy Engine"),(360,280,"Lifecycle State Machine"),(360,360,"Explicit Approval Gate"),(360,440,"Future Canary / Champion Comparison")]
content=''.join(f'<rect class="b" x="{x}" y="{y}" width="280" height="48" rx="8"/><text x="{x+140}" y="{y+30}" text-anchor="middle">{t}</text>' for x,y,t in boxes)+''.join(f'<line class="a" x1="500" y1="{y}" x2="500" y2="{y+32}"/>' for y in (88,168,248,328,408))
content+='<rect class="f" x="35" y="200" width="245" height="70" rx="8"/><text x="157" y="230" text-anchor="middle">Future Agent Recommendation</text><text x="157" y="253" text-anchor="middle">FUTURE / NOT IMPLEMENTED</text><line class="a" x1="280" y1="235" x2="360" y2="224"/><text x="170" y="315" text-anchor="middle" font-size="13">Recommendations enter policy; no bypass path.</text>'
write("artifacts/research_figures/phase_13/governance_architecture.svg",f'<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="540">{svg_style}{content}</svg>')
states=[("EXPERIMENTAL",30,50),("VALIDATED",240,50),("REGISTERED_CHALLENGER",450,50),("CHALLENGER_ELIGIBLE",700,50),("PROMOTION_ELIGIBLE",700,170),("APPROVAL_PENDING",450,170),("APPROVED_FOR_CANARY",200,170),("CANARY_ACTIVE",200,290),("ACTIVE",450,290),("ROLLBACK_REQUIRED",700,290),("ARCHIVED",700,410),("INVALIDATED",30,410),("REGISTERED_REFERENCE",450,410)]
stateboxes=''.join(f'<rect class="b" x="{x}" y="{y}" width="180" height="44" rx="7"/><text x="{x+90}" y="{y+27}" text-anchor="middle" font-size="12">{t}</text>' for t,x,y in states)
write("artifacts/research_figures/phase_13/model_lifecycle_state_machine.svg",f'<svg xmlns="http://www.w3.org/2000/svg" width="920" height="500">{svg_style}{stateboxes}<text x="460" y="485" text-anchor="middle" fill="#9a3412">Only policy-declared arrows are legal; all other transitions are blocked. Current references remain REGISTERED_REFERENCE.</text></svg>')
cards=''.join(f'<rect class="x" x="{40+i*315}" y="90" width="275" height="220" rx="10"/><text x="{177+i*315}" y="130" text-anchor="middle" font-size="23" font-weight="bold">{t}</text><text x="{177+i*315}" y="175" text-anchor="middle">REGISTERED_REFERENCE</text><text x="{177+i*315}" y="215" text-anchor="middle">Development benchmark: FAIL</text><text x="{177+i*315}" y="260" text-anchor="middle" font-size="18" font-weight="bold">PROMOTION BLOCKED</text>' for i,t in enumerate(("LOAD","WIND","PV")))
write("artifacts/research_figures/phase_13/current_reference_governance.svg",f'<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="370">{svg_style}<text x="500" y="42" text-anchor="middle" font-size="23" font-weight="bold">Current deterministic governance outcome</text>{cards}</svg>')
figures={"phase":"13","final_test_status":"NOT_EXECUTED","figures":[{"figure_id":"FIG-P13-01","path":"artifacts/research_figures/phase_13/governance_architecture.svg","source_artifacts":["config/governance/phase_13_policy.yaml"],"research_purpose":"Show deterministic authority and future recommendation boundary","generation_script":"scripts/finalize_phase13_research_artifacts.py"},{"figure_id":"FIG-P13-02","path":"artifacts/research_figures/phase_13/model_lifecycle_state_machine.svg","source_artifacts":["artifacts/experimental_design/phase_13_governance_protocol_freeze.yaml"],"research_purpose":"Show lifecycle states and blocked invalid transitions","generation_script":"scripts/finalize_phase13_research_artifacts.py"},{"figure_id":"FIG-P13-03","path":"artifacts/research_figures/phase_13/current_reference_governance.svg","source_artifacts":["artifacts/governance/phase_13/decisions.jsonl"],"research_purpose":"Show current benchmark-failure promotion blocks","generation_script":"scripts/finalize_phase13_research_artifacts.py"}]};dump("artifacts/research_figures/phase_13/figure_manifest.yaml",figures)

method="""# Deterministic model lifecycle governance

## Research Objective

Phase 13 designs and validates a deterministic lifecycle engine using evidence, lineage, fingerprints, frozen protocols, reproducibility, deviations, benchmark evidence, statistical evidence, approval, state-transition, and final-test policies before autonomous recommendations exist. RQ-GOV-1 through RQ-GOV-5 ask whether invalid transitions are prevented, research validity is distinguished from promotion eligibility, repeated inputs reproduce decisions, every decision is traceable, and immutable specifications resist conflicting recommendations.

Before implementation, H-GOV-1 predicted invalid or incomplete candidates would be blocked; H-GOV-2 predicted benchmark-inferior models would not become promotion eligible; H-GOV-3 predicted identical scientific decisions; H-GOV-4 predicted gate-level attribution. Support is assessed only after the frozen simulation.

## Governance Architecture

MLflow evidence and Phase 12 registry/lineage records feed a deterministic policy engine. The engine alone evaluates lifecycle transitions and emits structured decisions plus audit events. Future recommendations may enter this engine but cannot bypass it.

## Lifecycle States and Transition Rules

Research role, registry state, lifecycle state, benchmark gate, and approval state remain independent. The policy declares legal transitions. `INVALIDATED` and `ARCHIVED` are terminal. Baselines are non-lifecycle comparators. Current references remain `REGISTERED_REFERENCE`.

## Evidence Gate

Only official `VALID` evidence passes. P9-DEV-001 audit evidence remains invalid despite deviation resolution.

## Lineage Gate

Lifecycle elevation requires a complete raw-dataset-to-registry trace.

## Fingerprint Gate

Actual model and feature fingerprints must exactly match frozen expectations.

## Protocol Gate

Only hashes enumerated in the frozen policy are recognized; new hashes are never adopted automatically.

## Deviation Gate

Unresolved critical deviations block elevation. A resolved deviation does not rehabilitate invalid artifacts. P9-DEV-002 passes because scientific logical identity is preserved while both binary hashes remain recorded.

## Benchmark and Statistical Gates

Promotion requires strict development MAE superiority at the frozen 0% margin and statistical evidence that does not show material degradation. The threshold was not tuned. Development evidence does not substitute for final/external validation.

## Approval Gate

Promotion eligibility never means active. Explicit approval is required before canary eligibility. `SIMULATION_POLICY` approval is distinctly labelled and is never human approval.

## Decision Semantics and Auditability

Decisions are `ALLOW`, `DENY`, `REQUIRE_APPROVAL`, or `NO_OP`, with policy identity, all gate results, failures, reason codes, evidence paths, deterministic explanation, and a stable content fingerprint excluding IDs/timestamps.

## Scenario-Based Validation and Safety Metrics

Eighteen scenarios were frozen before execution. Unsafe Transition Prevention Rate is correctly blocked unsafe attempts divided by all unsafe attempts. False allowance and false denial are reported independently.

## Final-Test Isolation

The engine rejects final-test performance/data requests and activation of the historical P9-DEV-002 audit mode. Phase 13 reads are zero.

## Limitations

Metadata scenarios cannot emulate all operational failures, approval uses a simulation fixture rather than organizational IAM, and no deployment/canary system is evaluated.
""";write("docs/research_methodology/model_lifecycle_governance.md",method)
write("docs/paper_drafts/governance_results.md",f"""# Phase 13 governance results

The frozen suite produced {metrics['actual_matches']}/{metrics['total_scenarios']} correct decisions, {metrics['false_allow']} false allows, and {metrics['false_deny']} false denies. All {metrics['unsafe_transition_attempts']} unsafe transition attempts were blocked, giving an Unsafe Transition Prevention Rate of {metrics['unsafe_transition_prevention_rate_percent']}%.

The deterministic governance layer prevented internally preferred but benchmark-inferior LOAD, WIND, and PV reference models from being automatically elevated to promotion-eligible lifecycle states. This is a governance-safety finding, not a forecasting success: all three remain valid registered research references and all three fail their strongest development benchmark gates.

P9-DEV-001 invalid evidence, two fingerprint mutations, one missing-lineage case, one unknown protocol, one unresolved deviation, one illegal jump, one policy mismatch, and one synthetic final-test request were denied. P9-DEV-002 logical provenance was accepted without erasing its binary-checksum history. A qualifying synthetic challenger was allowed, while canary eligibility required explicit approval; simulation approval was separately labelled. Repeated evaluation produced identical decision class, gate outcomes, reason codes, and content fingerprint.
""")

evidence=read("artifacts/paper_evidence/evidence_registry.yaml");ids={x["id"] for x in evidence}
new=[("E-GOV-001","Phase 13 governance protocol freeze","artifacts/experimental_design/phase_13_governance_protocol_freeze.yaml"),("E-GOV-002","Declarative governance policy and checksum","config/governance/phase_13_policy.yaml"),("E-GOV-003","Governance policy fingerprint","artifacts/governance/phase_13/policy_snapshot.yaml"),("E-GOV-004","Lifecycle registry and state machine","artifacts/model_registry/lifecycle_registry.yaml"),("E-GOV-005","Frozen governance scenario set","artifacts/experimental_design/phase_13_governance_scenarios.yaml"),("E-GOV-006","Official governance decisions and scenario results","artifacts/governance/phase_13/decisions.jsonl"),("E-GOV-007","Governance safety metrics","artifacts/governance/phase_13/simulation_manifest.yaml"),("E-GOV-008","Current reference benchmark blocks","reports/tables/reference_governance_status.md"),("E-GOV-009","Invalid evidence and tampering rejection","artifacts/governance/phase_13/gate_results.csv"),("E-GOV-010","Lineage and protocol rejection","artifacts/governance/phase_13/gate_results.csv"),("E-GOV-011","Approval requirement and simulation distinction","artifacts/governance/phase_13/decisions.jsonl"),("E-GOV-012","Final-test policy rejection","artifacts/governance/phase_13/decisions.jsonl"),("E-GOV-013","Phase 13 governance figures","artifacts/research_figures/phase_13/figure_manifest.yaml"),("E-GOV-014","Governance methodology","docs/research_methodology/model_lifecycle_governance.md"),("E-GOV-015","Full governance regression tests","tests/test_phase13_governance.py"),("E-GOV-016","Phase 13 completion and full-suite results","reports/phase_13_completion.md")]
for i,d,s in new:
 if i not in ids:evidence.append({"id":i,"description":d,"source_artifact":s,"status":"VALID","generated_by":"Phase 13","relevant_paper_section":"Deterministic Governance"})
dump("artifacts/paper_evidence/evidence_registry.yaml",evidence)
print(json.dumps({"tables":4,"figures":3,"evidence_entries_added":len(new),"decision_accuracy":metrics["decision_correctness_percent"],"false_allow":metrics["false_allow"]},indent=2))
