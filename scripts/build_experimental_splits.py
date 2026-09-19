#!/usr/bin/env python3
"""Build the deterministic experimental splits (train/validation/test) from the canonical datasets."""
from __future__ import annotations

from _scriptlog import get_logger  # scripts/_scriptlog.py: stdout logging, SMARTGRID_MLOPS_LOG_LEVEL
log = get_logger('build_experimental_splits')

import argparse, csv, hashlib, json, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from smartgrid_mlops.experimental_design.rolling_origin import fold_boundaries,fold_membership
from smartgrid_mlops.experimental_design.splits import load_feature_rows,split_rows,stable_checksum
from smartgrid_mlops.experimental_design.validation import validate_temporal_order

FEATURES=ROOT/"data/processed/features"; OUT=ROOT/"artifacts/experimental_design"; TABLES=ROOT/"artifacts/research_tables"; REPORT_TABLES=ROOT/"reports/tables"

def iso(value): return value.isoformat() if value is not None else None
def build_all():
    OUT.mkdir(parents=True,exist_ok=True);TABLES.mkdir(parents=True,exist_ok=True);REPORT_TABLES.mkdir(parents=True,exist_ok=True)
    manifests=[];folds=[]
    for target in ("load","wind","pv"):
        for horizon in (1,24):
            path=FEATURES/target/f"h{horizon}/combined_v1.parquet";rows=load_feature_rows(path);parts=split_rows(rows)
            validate_temporal_order(parts["TRAIN"],parts["VALIDATION"]);validate_temporal_order(parts["VALIDATION"],parts["TEST"])
            manifest={"target":target,"horizon":horizon,"feature_set":"combined_v1","train_start":"2020-01-01T00:00:00","train_end":"2020-08-31T23:00:00","validation_start":"2020-09-01T00:00:00","validation_end":"2020-10-31T23:00:00","test_start":"2020-11-01T00:00:00","test_end":"2020-12-31T23:00:00","final_test_status":"LOCKED","train_samples":len(parts["TRAIN"]),"validation_samples":len(parts["VALIDATION"]),"test_samples":len(parts["TEST"]),"first_forecast_origin":iso(rows[0]["forecast_origin"]),"last_forecast_origin":iso(rows[-1]["forecast_origin"]),"first_target_timestamp":iso(rows[0]["target_timestamp"]),"last_target_timestamp":iso(rows[-1]["target_timestamp"])}
            manifest["split_checksum"]=stable_checksum(manifest);(OUT/f"split_manifest_{target}_h{horizon}.yaml").write_text(json.dumps(manifest,indent=2)+"\n");manifests.append(manifest)
            for boundary in fold_boundaries():
                train,val=fold_membership(rows,boundary);validate_temporal_order(train,val)
                folds.append({"target":target,"horizon":horizon,"fold_id":boundary["fold_id"],"training_start":iso(boundary["training_start"]),"training_end":iso(max((r["target_timestamp"] for r in train),default=None)),"validation_start":iso(boundary["validation_start"]),"validation_end":iso(max((r["target_timestamp"] for r in val),default=None)),"train_samples":len(train),"validation_samples":len(val)})
    fold_doc={"policy":"expanding_window","final_test_excluded":True,"folds":folds};fold_doc["checksum"]=stable_checksum(fold_doc);(OUT/"rolling_origin_folds.yaml").write_text(json.dumps(fold_doc,indent=2)+"\n")
    fields=["Partition","Start","End","Purpose"]
    rows=[{"Partition":"Training","Start":"2020-01-01","End":"2020-08-31","Purpose":"Model fitting"},{"Partition":"Validation","Start":"2020-09-01","End":"2020-10-31","Purpose":"Model selection"},{"Partition":"Final Test","Start":"2020-11-01","End":"2020-12-31","Purpose":"Locked unbiased evaluation"}]
    with (TABLES/"temporal_split_protocol.csv").open("w",newline="") as stream: writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(rows)
    (REPORT_TABLES/"temporal_split_protocol.md").write_text("# Temporal split protocol\n\n| Partition | Start | End | Purpose |\n| --- | --- | --- | --- |\n"+"\n".join(f"| {r['Partition']} | {r['Start']} | {r['End']} | {r['Purpose']} |" for r in rows)+"\n")
    from smartgrid_mlops.data_audit.reporting import _write_png
    figure_dir=ROOT/"artifacts/research_figures/phase_05";figure_dir.mkdir(parents=True,exist_ok=True)
    design=[1.0]*244+[2.0]*61+[3.0]*61
    figure_path=figure_dir/"temporal_evaluation_design.png";_write_png(figure_path,design,"Temporal evaluation design")
    figure_manifest=[{"figure_id":"FIG-EXP-001","title":"Temporal holdout and expanding-window evaluation design","source_dataset":"rts_gmlc_processed_v1 feature matrices","variables":["target_timestamp","partition","fold"],"date_range":"2020-01-01 through 2020-12-31","generation_script":"scripts/build_experimental_splits.py","purpose":"Research methodology visualization; no model results"}]
    (figure_dir/"figure_manifest.yaml").write_text(json.dumps(figure_manifest,indent=2)+"\n")
    return {"manifests":manifests,"rolling_folds":folds,"rolling_checksum":fold_doc["checksum"]}

if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--all",action="store_true");args=parser.parse_args()
    if not args.all: parser.error("--all is required")
    log.info(json.dumps({'split_manifests': len(result['manifests']), 'fold_records': len(result['rolling_folds']), 'rolling_checksum': result['rolling_checksum']}, indent=2))
