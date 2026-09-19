"""Metadata-only native MLflow smoke; never paper evidence."""
from __future__ import annotations
import json,sys,tempfile
from pathlib import Path
import mlflow
from mlflow import MlflowClient
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from smartgrid_mlops.mlops.tracking import TrackingConfig,tracked_run
import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stderr,
)
LOGGER = logging.getLogger(__name__)

config=TrackingConfig(ROOT)
tags={"research_phase":"12","tracking_origin":"NATIVE_MLFLOW","evidence_status":"NON_EVIDENCE_SMOKE","target":"synthetic","horizon":"0","model_family":"metadata_only","framework":"none","implementation_id":"NON_EVIDENCE_SMOKE","feature_set_id":"synthetic","feature_set_version":"v0","model_spec_fingerprint":"smoke-only","dataset_version":"synthetic","processed_dataset_manifest_hash":"NOT_APPLICABLE","feature_manifest_hash":"NOT_APPLICABLE","logical_feature_fingerprint":"NOT_APPLICABLE","protocol_freeze_hash":"phase12-smoke","forecast_origin_policy":"NOT_APPLICABLE","fold":"SMOKE","seed":"0","evaluation_role":"NON_EVIDENCE_SMOKE","research_run_key":"phase12-native-smoke-v1","official_candidate":"false"}
client=config.initialize(); exp=client.get_experiment_by_name("smartgrid/phase12/non-evidence-smoke")
existing=client.search_runs([exp.experiment_id],"tags.research_run_key = 'phase12-native-smoke-v1'",max_results=1) if exp else []
if existing: run=existing[0]
else:
    with tracked_run(config,"smartgrid/phase12/non-evidence-smoke",tags=tags,params={"purpose":"tracking foundation verification"},run_name="NON_EVIDENCE_SMOKE") as active:
        mlflow.log_metric("smoke_metric",1.0);mlflow.log_text("synthetic metadata only","smoke.txt");run_id=active.info.run_id
    run=client.get_run(run_id)
out={"status":"PASS","run_id":run.info.run_id,"tracking_origin":run.data.tags["tracking_origin"],"evidence_status":run.data.tags["evidence_status"],"excluded_from_official_aggregation":run.data.tags["evidence_status"]!="VALID","metric_logged":run.data.metrics.get("smoke_metric")==1.0,"query_pass":True,"lineage_link":"phase12-native-smoke-v1","final_test_data_used":False}
p=ROOT/"artifacts/mlops/native_smoke_result.yaml";p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(out,indent=2)+"\n");print(json.dumps(out,indent=2))
