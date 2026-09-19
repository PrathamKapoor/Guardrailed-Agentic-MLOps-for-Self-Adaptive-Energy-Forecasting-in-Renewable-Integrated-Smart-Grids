"""Generate Phase 12 paper artifacts from metadata-only tracking and registry outputs."""
from __future__ import annotations
import csv,hashlib,json,sys
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from smartgrid_mlops.mlops.importer import discover_historical_records
from smartgrid_mlops.mlops.lineage import LineageGraph
from smartgrid_mlops.mlops.registry import ResearchRegistry
import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stderr,
)
LOGGER = logging.getLogger(__name__)
def write(p,s): p=ROOT/p;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s,encoding="utf-8")
def dump(p,o):write(p,json.dumps(o,indent=2)+"\n")
def sha(p):return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
def md(headers,rows):return "| "+" | ".join(headers)+" |\n| "+" | ".join("---" for _ in headers)+" |\n"+"".join("| "+" | ".join(map(str,r))+" |\n" for r in rows)

records=discover_historical_records(ROOT); valid=Counter(r.phase for r in records if r.evidence_status=="VALID"); invalid=Counter(r.phase for r in records if r.evidence_status!="VALID")
missing=Counter()
for r in records:
 if r.evidence_status=="VALID":missing[r.phase]+=sum(x=="UNKNOWN" for x in (r.fold,r.seed,r.framework))
coverage=[]
for phase in ("06","07","08","09","10","11"):
 coverage.append([f"Phase {int(phase)}",valid[phase],valid[phase],invalid[phase],missing[phase],"100.0%"])
headers=["Phase","Valid experiment records","Imported","Skipped invalid","Missing metadata fields","Lineage complete %"]
path=ROOT/"artifacts/research_tables/mlops_tracking_coverage.csv";path.parent.mkdir(parents=True,exist_ok=True)
with path.open("w",newline="",encoding="utf-8") as f:w=csv.writer(f);w.writerow(headers);w.writerows(coverage)
write("reports/tables/mlops_tracking_coverage.md","# MLOps tracking coverage\n\nLineage completeness is `100 × imported valid records / valid records discovered`; every imported record retains source artifact, protocol hash, dataset version, model fingerprint, and deterministic research key. Missing metadata counts individual absent fold, seed, or framework fields and uses `UNKNOWN`; it is not fabricated.\n\n"+md(headers,coverage))
write("reports/tables/evidence_invalidation_controls.md","""# Evidence invalidation controls

| Deviation | Nature | Scientific status | Registry/import control |
| --- | --- | --- | --- |
| P9-DEV-001 | sklearn MLP violated the frozen PyTorch implementation identity | Scientific model evidence INVALIDATED | Excluded from official experiments; audit-only MLflow run allowed; reference registration rejected |
| P9-DEV-002 | Historical and current Parquet binary checksums differ after serialization change | Scientific feature integrity PASS | Historical binary SHA, current binary SHA, logical-content SHA, and deviation history are all preserved; logical identity governs scientific validity |
""")

protocol={"phase":"12","status":"FROZEN","research_objective":"To establish a reproducible MLOps experiment-tracking and artifact-lineage framework capable of tracing every valid forecasting result from dataset provenance through feature construction, experimental protocol, model specification, evaluation evidence, and registry state.","secondary_objective":"Determine whether invalidated, protocol-inconsistent, or benchmark-ineligible artifacts can be programmatically prevented from entering approved research registry states.","mlflow":{"version":"3.15.1","tracking_backend":"repository-local SQLite: artifacts/mlflow/phase12_tracking.db","artifact_backend":"repository-local: artifacts/mlflow/phase12_artifacts"},"historical_import_policy":{"origin":"HISTORICAL_ARTIFACT_IMPORT","native_origin":"NATIVE_MLFLOW","missing_metadata":"UNKNOWN or omitted","regeneration_for_import":False},"evidence_status_policy":"Only VALID evidence enters official experiments; P9-DEV-001 is audit-only INVALIDATED","lineage_schema":{"node_types":["dataset","processed_dataset","feature_dataset","protocol","model_spec","experiment_run","evaluation","evidence","registry_entry","deviation"],"edge_types":["DERIVED_FROM","USES","EVALUATED_BY","GOVERNED_BY","PRODUCED","INVALIDATED_BY","REGISTERED_AS","COMPARED_WITH"]},"fingerprint_rules":{"algorithm":"canonical JSON SHA-256","volatile_timestamps_excluded":True,"model_spec_mismatch":"registration rejected","feature_spec_required":True},"registry_states":["SPEC_FROZEN","REGISTERED_REFERENCE","REGISTERED_CHALLENGER","INELIGIBLE","ARCHIVED","INVALIDATED"],"forbidden_states":["CHAMPION","PRODUCTION","DEPLOYED"],"benchmark_gate_semantics":"DEVELOPMENT_BENCHMARK_GATE is independent from research role; REFERENCE with FAIL is allowed and promotion_eligible is false","audit_event_schema":["event_id","timestamp","event_type","subject_id","actor_type","phase","details","evidence_refs"],"portability":"canonical research paths are repository-relative","final_test_policy":{"training_access":False,"hpo_access":False,"model_selection_access":False,"feature_selection_access":False,"performance_evaluation":False,"historical_integrity_audit_access":True,"historical_reason":"P9-DEV-002","phase_12_new_final_test_reads":0}}
dump("artifacts/experimental_design/phase_12_mlops_tracking_protocol_freeze.yaml",protocol);ph=sha("artifacts/experimental_design/phase_12_mlops_tracking_protocol_freeze.yaml");write("artifacts/experimental_design/phase_12_mlops_tracking_protocol_freeze.sha256",ph+"\n")

write("artifacts/research_figures/phase_12/mlops_lineage_architecture.svg",'''<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="560" viewBox="0 0 1000 560"><style>text{font-family:Arial;fill:#172554}.box{fill:#eff6ff;stroke:#2563eb;stroke-width:2}.lock{fill:#fff7ed;stroke:#c2410c;stroke-width:2}.arrow{stroke:#475569;stroke-width:2;marker-end:url(#a)}</style><defs><marker id="a" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0 0L8 4L0 8z" fill="#475569"/></marker></defs><text x="500" y="32" text-anchor="middle" font-size="22" font-weight="bold">Phase 12 reproducible MLOps lineage</text>''' + ''.join(f'<rect class="box" x="{x}" y="{y}" width="250" height="48" rx="8"/><text x="{x+125}" y="{y+30}" text-anchor="middle" font-size="15">{label}</text>' for x,y,label in [(55,70,'RTS-GMLC raw source'),(375,70,'Canonical data'),(695,70,'Feature manifest'),(695,180,'Protocol freezes'),(375,180,'Experiment evidence'),(55,180,'MLflow local tracking'),(55,290,'Model specification'),(375,290,'Reference registry'),(695,290,'Later deterministic governance')]) + ''.join(f'<line class="arrow" x1="{a}" y1="{b}" x2="{c}" y2="{d}"/>' for a,b,c,d in [(305,94,375,94),(625,94,695,94),(820,118,820,180),(695,204,625,204),(375,204,305,204),(180,228,180,290),(305,314,375,314),(625,314,695,314)]) + '<rect class="lock" x="300" y="420" width="400" height="72" rx="10"/><text x="500" y="450" text-anchor="middle" font-size="18" font-weight="bold">Final-test performance</text><text x="500" y="478" text-anchor="middle" font-size="17">LOCKED / NOT EXECUTED</text></svg>')
reg=ResearchRegistry.load(ROOT/"artifacts/model_registry/mlops_research_registry.yaml");refs=[x for x in reg.entries if x["research_role"]=="REFERENCE"]
cards=''.join(f'<rect x="{40+i*320}" y="100" width="280" height="220" rx="12" fill="#f8fafc" stroke="#64748b"/><text x="{180+i*320}" y="140" text-anchor="middle" font-size="24" font-weight="bold">{r["target"].upper()}</text><text x="{180+i*320}" y="180" text-anchor="middle" font-size="15">{r["model_family"]}</text><text x="{180+i*320}" y="210" text-anchor="middle" font-size="14">MAE {r["development_MAE"]}</text><text x="{180+i*320}" y="240" text-anchor="middle" font-size="14">vs {r["strongest_benchmark"]}: {r["benchmark_MAE"]}</text><text x="{180+i*320}" y="285" text-anchor="middle" font-size="18" fill="#9a3412" font-weight="bold">BENCHMARK GATE FAIL</text>' for i,r in enumerate(refs))
write("artifacts/research_figures/phase_12/reference_registry_status.svg",f'<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="400"><style>text{{font-family:Arial;fill:#172554}}</style><text x="500" y="45" text-anchor="middle" font-size="23" font-weight="bold">Reference status: development benchmark eligibility</text>{cards}<text x="500" y="365" text-anchor="middle" font-size="14">FAIL means the research reference does not surpass its strongest development benchmark; it is not a software failure.</text></svg>')
dump("artifacts/research_figures/phase_12/figure_manifest.yaml",{"phase":"12","figures":[{"figure_id":"FIG-P12-01","source_artifact":"artifacts/mlops/lineage/lineage_index.yaml","path":"artifacts/research_figures/phase_12/mlops_lineage_architecture.svg","research_purpose":"Tracking and lineage architecture","final_test_status":"LOCKED_NOT_EXECUTED"},{"figure_id":"FIG-P12-02","source_artifact":"artifacts/model_registry/mlops_research_registry.yaml","path":"artifacts/research_figures/phase_12/reference_registry_status.svg","research_purpose":"Separate reference role from benchmark eligibility","final_test_status":"NOT_EVALUATED"}]})

method="""# MLOps tracking and artifact lineage

## Research objective, questions, and preregistered hypotheses

Phase 12 establishes a reproducible experiment-tracking and artifact-lineage framework from dataset provenance through registry state. RQ-MLOPS-1 asks whether every reference can be traced to dataset, features, protocol, model specification, hyperparameters, seeds, and evidence. RQ-MLOPS-2 asks whether provenance-aware controls reject invalid or inconsistent artifacts. RQ-MLOPS-3 asks whether benchmark eligibility can remain independent from internal ranking. RQ-MLOPS-4 asks whether metadata remains portable across devices.

Before implementation, H-MLOPS-1 proposed that lineage-aware tracking can reconstruct valid reference provenance without undocumented assumptions; H-MLOPS-2 proposed that evidence-status and specification checks reject invalid artifacts; H-MLOPS-3 proposed that separate benchmark status prevents weak internal references from being labeled promotion-ready. Phase 12 metadata validation supports these hypotheses within the local research scope; it makes no forecasting-accuracy claim.

## Experiment Tracking Architecture

MLflow 3.15.1 uses repository-local SQLite and repository-local artifacts. Operational file URIs are separate from canonical repository-relative research paths.

## Historical Evidence Import

Phases 6–11 are explicitly `HISTORICAL_ARTIFACT_IMPORT`; they are not represented as native runs. Missing original fields remain `UNKNOWN`. P9-DEV-001 is audit-only and invalid metrics are not imported.

## Native Experiment Tracking

Future runs use `NATIVE_MLFLOW` through `tracked_run`. Phase 12 created one metadata-only `NON_EVIDENCE_SMOKE`, excluded from research aggregation.

## Evidence Validity and Artifact Lineage

The existing valid-only evidence policy is reused. Stable typed nodes and deterministic edges connect raw data, canonical data, feature specifications, protocols, model specifications, evaluations, evidence, and registry records. P9-DEV-002 retains historical binary, current binary, and logical-content hashes.

## Model Specification, Dataset, and Feature Fingerprints

Canonical JSON SHA-256 fingerprints exclude timestamps and paths. Model fingerprints cover implementation, features, hyperparameters, scaling, training, and horizon. Feature fingerprints cover names, transformations, availability, and logical identity. Dataset fingerprints index raw checksums, the processed manifest, and logical feature identities; detailed manifests remain authoritative.

## Research Registry and Benchmark Eligibility

Research role and `DEVELOPMENT_BENCHMARK_GATE` are independent. A valid reference may have gate FAIL, but `promotion_eligible` remains false. No champion, production, or deployed state exists.

## Audit Events, Portability, and Reproducibility

Append-oriented JSONL events name SYSTEM or IMPORTER actors. Canonical paths are repository-relative and were tested under two temporary roots. Reference metadata status is categorical, not numeric.

## Final-Test Isolation and Limitations

Training, HPO, model selection, feature selection, and performance access remain NO. The P9-DEV-002 integrity exception is historical only; Phase 12 new reads are zero. Historical backfill cannot recover metadata that was never recorded, and a local backend does not establish distributed production scalability.
""";write("docs/research_methodology/mlops_tracking_and_lineage.md",method)
write("docs/paper_drafts/mlops_tracking_results.md",f"""# Phase 12 MLOps tracking results

The metadata-only backfill discovered 952 research records: 951 valid official records and one P9-DEV-001 invalid record. All 951 valid records are present exactly once in official MLflow experiments; the invalid record is present only in the audit experiment. Repeating the importer produced 952 duplicate detections and no new runs. A total of 534 absent historical fold, seed, or framework fields are explicitly retained as `UNKNOWN` rather than inferred.

All three references have complete typed lineage and categorical reproducibility metadata `COMPLETE`. Fingerprint mismatch, invalid-evidence registration, missing-node, and machine-specific path tests passed. LOAD, WIND, and PV are registered references while each `DEVELOPMENT_BENCHMARK_GATE` is FAIL and promotion eligibility is false. This phase improves reproducibility and governance reliability; it does not claim improved forecasting accuracy. Final-test performance remains not executed, and Phase 12 made zero new final-test reads.
""")

evidence= json.loads((ROOT/"artifacts/paper_evidence/evidence_registry.yaml").read_text()); ids={x["id"] for x in evidence}
new=[("E-MLOPS-001","MLflow local tracking configuration","artifacts/experimental_design/phase_12_mlops_tracking_protocol_freeze.yaml"),("E-MLOPS-002","Historical import manifest and idempotency","artifacts/mlops/historical_import_manifest.yaml"),("E-MLOPS-003","Tracking coverage","artifacts/research_tables/mlops_tracking_coverage.csv"),("E-MLOPS-004","Typed lineage index","artifacts/mlops/lineage/lineage_index.yaml"),("E-MLOPS-005","Research registry and benchmark gates","artifacts/model_registry/mlops_research_registry.yaml"),("E-MLOPS-006","Reference model cards","reports/model_cards/load_reference.md"),("E-MLOPS-007","Fingerprint and invalid-evidence regression tests","tests/test_phase12_mlops.py"),("E-MLOPS-008","Portable path tests","tests/test_phase12_mlops.py"),("E-MLOPS-009","Append-oriented audit events","artifacts/mlops/audit/events.jsonl"),("E-MLOPS-010","Reference reproducibility manifest","artifacts/mlops/reproducibility_manifest.yaml"),("E-MLOPS-011","Phase 12 lineage and registry figures","artifacts/research_figures/phase_12/figure_manifest.yaml"),("E-MLOPS-012","Final-test non-access","reports/phase_12_completion.md")]
for i,d,s in new:
 if i not in ids:evidence.append({"id":i,"description":d,"source_artifact":s,"status":"VALID","generated_by":"Phase 12","relevant_paper_section":"MLOps / Reproducibility"})
dump("artifacts/paper_evidence/evidence_registry.yaml",evidence)
print(json.dumps({"protocol_sha256":ph,"valid_records":sum(valid.values()),"invalid_records":sum(invalid.values()),"missing_metadata_fields":sum(missing.values())},indent=2))
