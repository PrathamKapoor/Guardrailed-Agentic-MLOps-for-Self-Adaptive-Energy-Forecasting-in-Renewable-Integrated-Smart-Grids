"""Idempotently backfill Phase 6–11 metadata; no forecasting data are opened."""
from __future__ import annotations
import argparse, json, platform, sys
from pathlib import Path
import mlflow
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from smartgrid_mlops.mlops.importer import discover_historical_records, import_records
from smartgrid_mlops.mlops.tracking import TrackingConfig
import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stderr,
)
LOGGER = logging.getLogger(__name__)

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--project-root",type=Path,default=ROOT);args=parser.parse_args();root=args.project_root.resolve()
    config=TrackingConfig(root); records=discover_historical_records(root)
    counts=import_records(config,records,root/"artifacts/mlops/audit/events.jsonl")
    manifest={"schema_version":"phase12-historical-import-v1","tracking_origin":"HISTORICAL_ARTIFACT_IMPORT","mlflow_version":mlflow.__version__,"python_version":platform.python_version(),"tracking_backend":"repository-local SQLite: artifacts/mlflow/phase12_tracking.db","artifact_backend":"repository-local: artifacts/mlflow/phase12_artifacts","import_granularity":"research-relevant rows from official phase metrics/tables; no epoch or checkpoint import","source_phases":[] ,**counts,"valid_records_present":counts["discovered"]-counts["invalid_skipped"],"audit_records_present":1,"audit_records_imported_separately":counts["audit_imported"],"invalid_p9_dev_001_officially_imported":False,"final_test_metrics_imported":False,"phase_12_new_final_test_reads":0}
    sources={}
    for r in records:
        item=sources.setdefault(r.phase,{"source_phase":r.phase,"source_artifacts":set(),"records_discovered":0,"mlflow_experiment":f"smartgrid/phase{r.phase}/"})
        item["source_artifacts"].add(r.source_artifact);item["records_discovered"]+=1
    manifest["source_phases"]=[{**v,"source_artifacts":sorted(v["source_artifacts"])} for _,v in sorted(sources.items())]
    out=root/"artifacts/mlops/historical_import_manifest.yaml";out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(counts,indent=2));return 0
if __name__=="__main__": raise SystemExit(main())
