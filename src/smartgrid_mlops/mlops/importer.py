from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import mlflow
from mlflow import MlflowClient

from .audit import append_audit_event
from .evidence import evidence_route
from .fingerprints import model_spec_fingerprint, research_run_key
from .schemas import AuditEvent, FINAL_TEST_TAGS
from .tracking import TrackingConfig, ensure_experiment

EXPERIMENTS = {
    "06": "smartgrid/phase06/baselines", "07": "smartgrid/phase07/classical",
    "08": "smartgrid/phase08/neural", "09": "smartgrid/phase09/hpo",
    "10": "smartgrid/phase10/ablation", "11": "smartgrid/phase11/reference-selection",
}
PROTOCOL_PATHS = {
    "06": "artifacts/experimental_design/protocol_freeze.yaml",
    "07": "artifacts/experimental_design/phase_07_model_protocol_freeze.yaml",
    "08": "artifacts/experimental_design/phase_08_neural_protocol_freeze.yaml",
    "09": "artifacts/experimental_design/phase_09_hpo_protocol_freeze.yaml",
    "10": "artifacts/experimental_design/phase_10_ablation_protocol_freeze.yaml",
    "11": "artifacts/experimental_design/phase_11_finalist_selection_protocol_freeze.yaml",
}


@dataclass
class ImportRecord:
    phase: str; target: str; horizon: int; model_family: str; framework: str
    implementation_id: str; feature_set_id: str; fold: str; seed: str
    evaluation_role: str; evidence_status: str; metrics: dict; params: dict; source_artifact: str
    model_fingerprint: str = ""

    def finalize(self):
        if not self.model_fingerprint:
            self.model_fingerprint = model_spec_fingerprint({"model_family": self.model_family, "framework": self.framework,
                "implementation_id": self.implementation_id, "feature_specification": self.feature_set_id,
                "hyperparameters": self.params.get("hyperparameters", "UNKNOWN"), "scaling_policy": self.params.get("scaling_policy", "UNKNOWN"),
                "training_policy": self.params.get("training_policy", "UNKNOWN"), "horizon": self.horizon})
        return self

    @property
    def key(self):
        return research_run_key(phase=self.phase, target=self.target, horizon=self.horizon,
            model_spec_fingerprint=self.model_fingerprint, feature_set=self.feature_set_id,
            fold=self.fold, seed=self.seed, evaluation_role=self.evaluation_role)


def _field(row, *names, default="UNKNOWN"):
    low = {k.lower(): v for k, v in row.items()}
    for name in names:
        value = low.get(name.lower())
        if value not in (None, "", "nan"): return value
    return default


def records_from_csv(root: Path, phase: str, relative: str, role: str) -> list[ImportRecord]:
    result=[]
    with (root/relative).open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            status=_field(row,"evidence_status",default="VALID")
            model=_field(row,"model","model_family","baseline","candidate",default="UNKNOWN")
            framework=_field(row,"framework",default="deterministic" if phase=="06" else "UNKNOWN")
            impl=_field(row,"implementation_id",default=str(model).upper())
            if phase == "08":
                framework = "pytorch"
                impl = "PYTORCH_MLP_V1" if str(model).lower() == "mlp" else f"PYTORCH_{str(model).upper()}_V1"
            metrics={}
            skipped_metrics=[]
            for metric in ("MAE","RMSE","sMAPE","nMAE","nRMSE"):
                aliases=(metric,metric.lower(),"objective_MAE","mae") if metric=="MAE" else (metric,metric.lower())
                raw=_field(row,*aliases,default=None)
                if raw is None: continue
                try:
                    metrics[metric]=float(raw)
                except (TypeError,ValueError):
                    # Unparsable cell: keep the import going but record the skip so
                    # the gap is visible in the imported record instead of silent.
                    skipped_metrics.append(metric)
            parameters={"historical_metadata_policy":"UNKNOWN_WHERE_NOT_RECORDED"}
            if skipped_metrics: parameters["unparsable_metric_fields"]=",".join(skipped_metrics)
            raw_hp=_field(row,"hyperparameters",default=None)
            if raw_hp is not None:
                try: parameters["hyperparameters"]=json.loads(raw_hp)
                except (TypeError,ValueError): parameters["hyperparameters"]=raw_hp
            for source,target_name in (("feature_count","feature_count"),("sequence_length","sequence_length"),("parameter_count","model_complexity"),("optimizer","optimizer"),("batch_size","batch_size"),("best_epoch","early_stopping_epoch")):
                value=_field(row,source,default=None)
                if value is not None: parameters[target_name]=value
            result.append(ImportRecord(phase,_field(row,"target").lower(),int(float(_field(row,"horizon",default=24))),model,framework,impl,
                _field(row,"feature_set","feature_set_id",default="NOT_APPLICABLE"),_field(row,"fold"),_field(row,"seed"),role,status,
                metrics,parameters,relative).finalize())
    return result


def discover_historical_records(root: Path) -> list[ImportRecord]:
    sources=[
      ("06","artifacts/experiments/baselines/phase_06/metrics/baseline_fold_metrics.csv","ROLLING_ORIGIN_EVALUATION"),
      ("07","artifacts/experiments/classical/phase_07/metrics/fold_metrics.csv","ROLLING_ORIGIN_EVALUATION"),
      ("08","artifacts/experiments/neural/phase_08/metrics/run_metadata.csv","ROLLING_ORIGIN_EVALUATION"),
      ("09","artifacts/research_tables/hpo_trial_history.csv","HPO_SEARCH_VALID"),
      ("09","artifacts/experiments/hpo/phase_09/post_hpo_validation/metrics.csv","POST_HPO_VALIDATION"),
      ("10","artifacts/experiments/ablation/phase_10/official/metrics/run_metrics.csv","FEATURE_ABLATION"),
      ("10","artifacts/experiments/ablation/phase_10/confirmation/metrics/run_metrics.csv","POST_ABLATION_CONFIRMATION"),
      ("11","artifacts/research_tables/forecasting_candidate_synthesis.csv","REFERENCE_SELECTION"),
    ]
    records=[]
    for phase,path,role in sources: records.extend(records_from_csv(root,phase,path,role))
    records.append(ImportRecord("09","multi",24,"mlp","sklearn","MLPRegressor","combined_v1","UNKNOWN","UNKNOWN","AUDIT_INVALIDATED_EVIDENCE","INVALIDATED",{},
        {"deviation_id":"P9-DEV-001","official_candidate":False},"artifacts/experiments/hpo/phase_09/invalid_neural_sklearn/INVALID_EVIDENCE.yaml").finalize())
    return records


def import_records(config: TrackingConfig, records: list[ImportRecord], audit_path: Path) -> dict:
    client=config.initialize(); counts={"discovered":len(records),"imported":0,"invalid_skipped":0,"audit_imported":0,"duplicates":0,"missing_metadata":0}
    counts["missing_metadata"] = sum(sum(1 for value in (r.fold, r.seed, r.framework) if value == "UNKNOWN") for r in records if r.evidence_status == "VALID")
    for record in records:
        route=evidence_route({"evidence_status":record.evidence_status,"framework":record.framework,"implementation_id":record.implementation_id,"model_family":record.model_family})
        if route == "AUDIT_ONLY":
            counts["invalid_skipped"]+=1
            exp_id=ensure_experiment(config,"AUDIT_INVALIDATED_EVIDENCE")
            existing=client.search_runs([exp_id],filter_string=f"tags.research_run_key = '{record.key}'",max_results=1)
            if existing: counts["duplicates"]+=1; continue
            tags={**FINAL_TEST_TAGS,"research_phase":record.phase,"tracking_origin":"HISTORICAL_ARTIFACT_IMPORT","evidence_status":"INVALIDATED","deviation_id":"P9-DEV-001","official_candidate":"false","research_run_key":record.key,"model_family":record.model_family,"framework":record.framework,"implementation_id":record.implementation_id,"evaluation_role":"AUDIT_INVALIDATED_EVIDENCE"}
            run=client.create_run(exp_id,tags=tags,run_name="P9-DEV-001-AUDIT-ONLY");client.set_terminated(run.info.run_id)
            counts["audit_imported"]+=1
            append_audit_event(audit_path,AuditEvent("EVIDENCE_INVALIDATED",record.key,"IMPORTER","12",{"deviation_id":"P9-DEV-001"},[record.source_artifact]))
            continue
        if route != "OFFICIAL": counts["invalid_skipped"]+=1; continue
        exp_id=ensure_experiment(config,EXPERIMENTS[record.phase])
        existing=client.search_runs([exp_id],filter_string=f"tags.research_run_key = '{record.key}'",max_results=1)
        protocol_hash=hashlib.sha256((config.project_root/PROTOCOL_PATHS[record.phase]).read_bytes()).hexdigest()
        if existing:
            client.set_tag(existing[0].info.run_id,"protocol_freeze_hash",protocol_hash)
            counts["duplicates"]+=1; continue
        tags={**FINAL_TEST_TAGS,"research_phase":record.phase,"tracking_origin":"HISTORICAL_ARTIFACT_IMPORT","evidence_status":"VALID",
              "target":record.target,"horizon":str(record.horizon),"model_family":record.model_family,"framework":record.framework,
              "implementation_id":record.implementation_id,"feature_set_id":record.feature_set_id,"feature_set_version":"v1",
              "model_spec_fingerprint":record.model_fingerprint,"dataset_version":"rts_gmlc_processed_v1","fold":record.fold,"seed":record.seed,
              "evaluation_role":record.evaluation_role,"research_run_key":record.key,"source_artifact":record.source_artifact,
              "forecast_origin_policy":"target-timestamp chronological rolling-origin","official_candidate":"true"}
        tags["protocol_freeze_hash"]=protocol_hash
        tags["processed_dataset_manifest_hash"]=hashlib.sha256((config.project_root/"data/manifests/processed_dataset_manifest.yaml").read_bytes()).hexdigest()
        tags["feature_manifest_hash"]=hashlib.sha256((config.project_root/"data/manifests/feature_manifest.yaml").read_bytes()).hexdigest()
        run=client.create_run(exp_id,tags=tags,run_name=record.key[:64])
        for key,value in record.params.items(): client.log_param(run.info.run_id,key,json.dumps(value,sort_keys=True) if isinstance(value,(dict,list)) else value)
        for key,value in record.metrics.items(): client.log_metric(run.info.run_id,key,value)
        client.set_terminated(run.info.run_id)
        counts["imported"]+=1
        append_audit_event(audit_path,AuditEvent("EXPERIMENT_IMPORTED",record.key,"IMPORTER","12",{"source_phase":record.phase},[record.source_artifact]))
    return counts
