"""Build Phase 12 metadata only. This script never opens forecasting datasets or predictions."""
from __future__ import annotations

import csv, hashlib, json, platform, subprocess, sys
from pathlib import Path

import mlflow

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from smartgrid_mlops.mlops.audit import append_audit_event
from smartgrid_mlops.mlops.fingerprints import dataset_fingerprint, feature_spec_fingerprint, model_spec_fingerprint
from smartgrid_mlops.mlops.lineage import LineageGraph
from smartgrid_mlops.mlops.registry import ResearchRegistry
from smartgrid_mlops.mlops.schemas import AuditEvent
import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stderr,
)
LOGGER = logging.getLogger(__name__)

def read(path): return json.loads((ROOT/path).read_text(encoding="utf-8"))
def sha(path): return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
def write(path,text): p=ROOT/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding="utf-8")
def dump(path,obj): write(path,json.dumps(obj,indent=2)+"\n")
def markdown_table(headers,rows):
    return "| "+" | ".join(headers)+" |\n| "+" | ".join("---" for _ in headers)+" |\n"+"".join("| "+" | ".join(str(x) for x in row)+" |\n" for row in rows)

phase10=read("artifacts/experimental_design/phase_10_ablation_protocol_freeze.yaml")
phase11=read("artifacts/model_registry/forecasting_reference_registry.yaml")
feature_manifest=read("data/manifests/feature_manifest.yaml")
processed=read("data/manifests/processed_dataset_manifest.yaml")
comparisons={r["target"]:r for r in csv.DictReader((ROOT/"artifacts/research_tables/development_paired_comparisons.csv").open())}
feature_sets=read("config/ablation/phase_10.yaml")["feature_sets"]
protocol_hash=sha("artifacts/experimental_design/phase_11_finalist_selection_protocol_freeze.yaml")
raw_hashes=sorted(line.strip().split()[0] for line in (ROOT/"data/manifests/rts_gmlc_checksums.sha256").read_text().splitlines() if line.strip())
processed_hash=sha("data/manifests/processed_dataset_manifest.yaml")
feature_manifest_hash=sha("data/manifests/feature_manifest.yaml")
logical={x["target"]:x.get("logical_content_sha256",x["checksum"]) for x in feature_manifest["entries"] if x["horizon"]==24}
dataset_fp=dataset_fingerprint({"raw_source_checksum_set":raw_hashes,"processed_manifest_hash":processed_hash,"logical_feature_fingerprints":logical})
classical={x["model"]:x for x in phase10["classical_models"].values()}

registry=ResearchRegistry(); graph=LineageGraph()
graph.add_node("dataset:rts-gmlc-v2.0","dataset",version="RTS-GMLC",manifest_path="data/manifests/rts_gmlc_manifest.yaml")
graph.add_node("processed:rts_gmlc_processed_v1","processed_dataset",manifest_path="data/manifests/processed_dataset_manifest.yaml",manifest_hash=processed_hash)
graph.add_edge("processed:rts_gmlc_processed_v1","dataset:rts-gmlc-v2.0","DERIVED_FROM")
graph.add_node("protocol:phase11-finalist-selection","protocol",path="artifacts/experimental_design/phase_11_finalist_selection_protocol_freeze.yaml",sha256=protocol_hash)
graph.add_node("evidence:phase11-selection","evidence",path="artifacts/research_tables/forecasting_candidate_synthesis.csv",status="VALID")
graph.add_node("deviation:P9-DEV-001","deviation",scientific_evidence="INVALIDATED",path="reports/phase_09_protocol_deviation.md")
graph.add_node("deviation:P9-DEV-002","deviation",scientific_integrity="PASS",historical_binary_sha256="1e4ca9fcb391587136b2def464da0685c6f6a9644b43cf9ff9b062e095ee61a1",current_binary_sha256="dc831266e3aab8f55534de91dcf9d744cedad2c0aa0997d2a7796944aeedc83d",logical_content_sha256="e96842a2c7ac3eeb64d54c29985f5ca3d56268e1f12c137440b783c965b4d5fb")

ref_rows=[]; lineage_rows=[]; repro={"schema_version":"phase12-reproducibility-v1","code_version":"UNKNOWN (repository has no committed HEAD)","library_versions":{"mlflow":mlflow.__version__,"python":platform.python_version(),"platform":platform.platform()},"references":[]}
for target in ("load","wind","pv"):
    ref=phase11[target]["reference_model"]; comp=comparisons[target]; model=ref["model"]
    hp=classical[model]["hyperparameters"]
    fdoc={"feature_set_id":ref["feature_set"],"feature_names":feature_sets[ref["feature_set"]],"transformations":"lags copied from combined_v1; no global scaling","forecast_horizon_availability_contract":"all sources at or before forecast origin for H24","logical_feature_identity":logical[target]}
    ffp=feature_spec_fingerprint(fdoc)
    mdoc={"model_family":model,"framework":ref["framework"],"implementation_id":ref["implementation_id"],"feature_specification":fdoc,"hyperparameters":hp,"scaling_policy":"none for tree estimator","training_policy":{"folds":["F05","F06"],"seed_policy":[42],"selection_source":"Phase 10 freeze"},"horizon":24}
    mfp=model_spec_fingerprint(mdoc); rid=f"MLOPS-REF-{target.upper()}-H24-V1"
    entry={"registry_id":rid,"target":target,"horizon":24,"research_role":"REFERENCE","registry_state":"REGISTERED_REFERENCE","model_family":model,"framework":ref["framework"],"implementation_id":ref["implementation_id"],"model_spec_fingerprint":mfp,"feature_set_id":ref["feature_set"],"feature_spec_fingerprint":ffp,"dataset_fingerprint":dataset_fp,"protocol_hash":protocol_hash,"development_primary_metric":"MAE","development_MAE":float(comp["MAE_candidate"]),"strongest_benchmark":comp["comparator"],"benchmark_MAE":float(comp["MAE_comparator"]),"development_benchmark_gate":"BENCHMARK_GATE_FAIL","evidence_status":"VALID","selection_evidence":["artifacts/model_registry/forecasting_reference_registry.yaml","artifacts/research_tables/development_paired_comparisons.csv"],"deviation_references":[{"id":"P9-DEV-002","status":"RESOLVED_SCIENTIFIC_INTEGRITY_PASS"}] if target=="load" else [],"created_from_phase":"11 (registered in Phase 12)","final_test_performance_status":"NOT_EVALUATED","promotion_eligible":False}
    registry.register(entry,expected_model_fingerprint=mfp)
    feature_id=f"feature:{target}:h24:{ref['feature_set']}"; model_id=f"model-spec:{mfp}"; eval_id=f"evaluation:phase11:{target}"; reg_id=rid
    graph.add_node(feature_id,"feature_dataset",feature_set_id=ref["feature_set"],feature_spec_fingerprint=ffp,path=f"data/processed/features/{target}/h24/combined_v1.parquet")
    graph.add_node(model_id,"model_spec",model_spec_fingerprint=mfp,config_path="artifacts/experimental_design/phase_10_ablation_protocol_freeze.yaml")
    graph.add_node(eval_id,"evaluation",development_MAE=float(comp["MAE_candidate"]),benchmark_MAE=float(comp["MAE_comparator"]),final_test="NOT_EVALUATED")
    graph.add_node(reg_id,"registry_entry",research_role="REFERENCE",registry_state="REGISTERED_REFERENCE")
    graph.add_edge(feature_id,"processed:rts_gmlc_processed_v1","DERIVED_FROM");graph.add_edge(model_id,feature_id,"USES");graph.add_edge(model_id,"protocol:phase11-finalist-selection","GOVERNED_BY");graph.add_edge(model_id,eval_id,"EVALUATED_BY");graph.add_edge(eval_id,"evidence:phase11-selection","PRODUCED");graph.add_edge("evidence:phase11-selection",reg_id,"REGISTERED_AS")
    if target=="load": graph.add_edge(feature_id,"deviation:P9-DEV-002","INVALIDATED_BY")
    ref_rows.append([target.upper(),model,ref["feature_set"],comp["MAE_candidate"],comp["comparator"],comp["MAE_comparator"],"FAIL",mfp,"COMPLETE","NOT_EVALUATED"])
    lineage_rows.append([target.upper(),rid,model,ref["feature_set"],"rts_gmlc_processed_v1","phase_11_finalist_selection",sha("artifacts/experimental_design/phase_10_ablation_protocol_freeze.yaml"),mfp,"development_paired_comparisons.csv","REGISTERED_REFERENCE"])
    repro["references"].append({"target":target,"registry_id":rid,"status":"COMPLETE","dataset_lineage":["data/manifests/rts_gmlc_manifest.yaml","data/manifests/processed_dataset_manifest.yaml"],"processed_dataset_hash":processed_hash,"feature_logical_fingerprint":logical[target],"feature_config":"config/ablation/phase_10.yaml","protocol_hashes":{"phase10":sha("artifacts/experimental_design/phase_10_ablation_protocol_freeze.yaml"),"phase11":protocol_hash},"model_spec_fingerprint":mfp,"hyperparameters":hp,"training_policy":{"scaling":"none for tree estimator","seed_policy":[42],"folds":["F05","F06"]},"development_evidence":{"MAE":float(comp["MAE_candidate"]),"benchmark":comp["comparator"],"benchmark_MAE":float(comp["MAE_comparator"])}})
    append_audit_event(ROOT/"artifacts/mlops/audit/events.jsonl",AuditEvent("MODEL_REGISTERED",rid,"SYSTEM","12",{"benchmark_gate":"BENCHMARK_GATE_FAIL","promotion_eligible":False},entry["selection_evidence"]))
    append_audit_event(ROOT/"artifacts/mlops/audit/events.jsonl",AuditEvent("BENCHMARK_GATE_FAILED",rid,"SYSTEM","12",{"meaning":"reference does not surpass strongest development benchmark"},entry["selection_evidence"]))
    ch=phase11[target]["challengers"][0]; ch_fdoc={"feature_set_id":ch["feature_set"],"feature_names":feature_sets[ch["feature_set"]],"transformations":"combined_v1","forecast_horizon_availability_contract":"origin-available H24 features","logical_feature_identity":logical[target]}; ch_ffp=feature_spec_fingerprint(ch_fdoc)
    ch_cfg=read(f"artifacts/experiments/hpo/phase_09/best_configs/{target}_pytorch_mlp.yaml")
    ch_mfp=model_spec_fingerprint({"model_family":"mlp","framework":"pytorch","implementation_id":"PYTORCH_MLP_V1","feature_specification":ch_fdoc,"hyperparameters":ch_cfg["hyperparameters"],"scaling_policy":{"features":ch_cfg["feature_scaling_policy"],"target":ch_cfg["target_scaling_policy"]},"training_policy":{"loss":ch_cfg["training_loss"],"optimizer":ch_cfg["optimizer_family"],"early_stopping":ch_cfg["inner_early_stopping_policy"]},"horizon":24})
    registry.register({"registry_id":f"MLOPS-CHAL-{target.upper()}-H24-MLP-V1","target":target,"horizon":24,"research_role":"CHALLENGER","registry_state":"REGISTERED_CHALLENGER","model_family":"mlp","framework":"pytorch","implementation_id":"PYTORCH_MLP_V1","model_spec_fingerprint":ch_mfp,"feature_set_id":"E_full","feature_spec_fingerprint":ch_ffp,"dataset_fingerprint":dataset_fp,"protocol_hash":protocol_hash,"development_primary_metric":"MAE","development_MAE":ch["mae"],"strongest_benchmark":comp["comparator"],"benchmark_MAE":float(comp["MAE_comparator"]),"development_benchmark_gate":"BENCHMARK_GATE_FAIL","evidence_status":"VALID","selection_evidence":["artifacts/experimental_design/phase_11_forecasting_finalist_freeze.yaml"],"deviation_references":[],"created_from_phase":"11 (registered in Phase 12)","final_test_performance_status":"NOT_EVALUATED","promotion_eligible":False})

for target in ("load","wind","pv"):
  for name in ("RTS_DAY_AHEAD","H24_DAILY_PERSISTENCE","H24_WEEKLY_PERSISTENCE"):
    bfp=model_spec_fingerprint({"model_family":name,"framework":"deterministic_baseline","implementation_id":name,"feature_specification":"NOT_APPLICABLE","hyperparameters":{},"scaling_policy":"NOT_APPLICABLE","training_policy":"deterministic comparator","horizon":24})
    registry.register({"registry_id":f"MLOPS-BASE-{target.upper()}-{name}","target":target,"horizon":24,"research_role":"BASELINE_COMPARATOR","registry_state":"SPEC_FROZEN","model_family":name,"framework":"deterministic_baseline","implementation_id":name,"model_spec_fingerprint":bfp,"feature_set_id":"NOT_APPLICABLE","feature_spec_fingerprint":"NOT_APPLICABLE","dataset_fingerprint":dataset_fp,"protocol_hash":sha("artifacts/experimental_design/protocol_freeze.yaml"),"development_primary_metric":"MAE","development_MAE":None,"strongest_benchmark":"NOT_APPLICABLE","benchmark_MAE":None,"development_benchmark_gate":"NOT_APPLICABLE","evidence_status":"VALID","selection_evidence":["artifacts/experiments/baselines/phase_06/metrics/baseline_validation_metrics.csv"],"deviation_references":[],"created_from_phase":"06 (registered in Phase 12)","final_test_performance_status":"NOT_EVALUATED","promotion_eligible":False})

invalid_fp=model_spec_fingerprint({"model_family":"mlp","framework":"sklearn","implementation_id":"MLPRegressor","feature_specification":"combined_v1","hyperparameters":"AUDIT_ONLY","scaling_policy":"INVALID_MISMATCH","training_policy":"INVALID_MISMATCH","horizon":24})
registry.register({"registry_id":"AUDIT-P9-DEV-001-SKLEARN-MLP","target":"multi","horizon":24,"research_role":"AUDIT_ONLY","registry_state":"INVALIDATED","model_family":"mlp","framework":"sklearn","implementation_id":"MLPRegressor","model_spec_fingerprint":invalid_fp,"feature_set_id":"combined_v1","feature_spec_fingerprint":"UNKNOWN","dataset_fingerprint":dataset_fp,"protocol_hash":sha("artifacts/experimental_design/phase_09_hpo_protocol_freeze.yaml"),"development_primary_metric":"MAE","development_MAE":None,"strongest_benchmark":"NOT_APPLICABLE","benchmark_MAE":None,"development_benchmark_gate":"NOT_APPLICABLE","evidence_status":"INVALIDATED","selection_evidence":["artifacts/experiments/hpo/phase_09/invalid_neural_sklearn/INVALID_EVIDENCE.yaml"],"deviation_references":[{"id":"P9-DEV-001","status":"RESOLVED_EVIDENCE_INVALIDATED"}],"created_from_phase":"09 audit","final_test_performance_status":"NOT_EVALUATED","promotion_eligible":False})
registry.validate_one_reference_per_target(); registry.dump(ROOT/"artifacts/model_registry/mlops_research_registry.yaml",{"phase11_selection_source":"artifacts/model_registry/forecasting_reference_registry.yaml","reference_is_not_promotion_eligible":True})
graph.validate();graph.dump(ROOT/"artifacts/mlops/lineage/lineage_index.yaml");dump("artifacts/mlops/reproducibility_manifest.yaml",repro)

headers=["Target","Reference Model","Feature Set","Development MAE","Strongest Benchmark","Benchmark MAE","Benchmark Gate","Model Fingerprint","Lineage Status","Final-Test Status"]
with (ROOT/"artifacts/research_tables/reference_registry_summary.csv").open("w",newline="",encoding="utf-8") as f: w=csv.writer(f);w.writerow(headers);w.writerows(ref_rows)
write("reports/tables/reference_registry_summary.md","# Reference registry summary\n\n"+markdown_table(headers,ref_rows))
lheaders=["Target","Reference ID","Model","Feature Set","Dataset Version","Protocol","Config Checksum","Model Fingerprint","Development Evidence","Registry Status"]
with (ROOT/"artifacts/research_tables/reference_model_lineage.csv").open("w",newline="",encoding="utf-8") as f:w=csv.writer(f);w.writerow(lheaders);w.writerows(lineage_rows)
write("reports/tables/reference_model_lineage.md","# Reference model lineage\n\n"+markdown_table(lheaders,lineage_rows))

for target,row in zip(("load","wind","pv"),ref_rows):
    text=f"""# {target.upper()} H24 research reference card

## Purpose

Frozen internally trained reference for subsequent bounded MLOps research.

## Specification and development evidence

- Target / horizon: {target.upper()} / H24
- Model family: {row[1]}
- Feature set: {row[2]}
- Development F05–F06 MAE: {row[3]}
- Strongest benchmark: {row[4]} (MAE {row[5]})
- DEVELOPMENT_BENCHMARK_GATE: FAIL
- Model specification fingerprint: `{row[7]}`
- Data lineage: RTS-GMLC → `rts_gmlc_processed_v1` → H24 feature manifest
- Feature lineage: `config/ablation/phase_10.yaml` → `{row[2]}`
- Protocol: Phase 10 fixed specification and Phase 11 development-only selection
- Final-test performance: NOT_EVALUATED

## Known limitations and intended role

Single-year research-system data, no meteorological covariates, and development-only evidence limit generalization. This model is the frozen internally trained research reference for subsequent MLOps experiments. It does not currently outperform the strongest development benchmark and must not be interpreted as production-promotion eligible.
"""
    write(f"reports/model_cards/{target}_reference.md",text)

dump("artifacts/mlops/build_summary.yaml",{"lineage_nodes":len(graph.nodes),"lineage_edges":len(graph.edges),"references":3,"challengers":3,"baselines":9,"invalidated_audit_records":1,"dataset_fingerprint":dataset_fp,"final_test_new_reads":0})
print(json.dumps({"registry_entries":len(registry.entries),"lineage_nodes":len(graph.nodes),"lineage_edges":len(graph.edges),"final_test_new_reads":0},indent=2))
