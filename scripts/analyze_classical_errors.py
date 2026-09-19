#!/usr/bin/env python3
"""Descriptive, validation-only Phase 7 error slices from preserved predictions."""
from __future__ import annotations
from _scriptlog import get_logger  # scripts/_scriptlog.py: stdout logging, SMARTGRID_MLOPS_LOG_LEVEL
log = get_logger('analyze_classical_errors')
import csv, sys, hashlib, json
from collections import defaultdict
from pathlib import Path
import pyarrow.parquet as pq

ROOT=Path(__file__).resolve().parents[1]

def write(path,rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("w",newline="",encoding="utf-8") as s:
        w=csv.DictWriter(s,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def main():
    rows=pq.read_table(ROOT/"artifacts/experiments/classical/phase_07/predictions/classical_predictions.parquet").to_pylist(); grouped=defaultdict(list)
    for r in rows: grouped[(r["target"],r["horizon"],r["model_family"],r["fold_id"],r["target_timestamp"])].append(r)
    mean=[]
    for values in grouped.values():
        r=values[0].copy();r["prediction"]=sum(x["prediction"] for x in values)/len(values);r["absolute_error"]=abs(r["actual"]-r["prediction"]);mean.append(r)
    by_model=defaultdict(list)
    for r in mean: by_model[(r["target"],r["horizon"],r["model_family"])].append(r)
    out=[]
    for key,vals in by_model.items():
        actuals=sorted(r["actual"] for r in vals);q1=actuals[len(actuals)//4];q3=actuals[(3*len(actuals))//4]
        slices=defaultdict(list)
        for r in vals:
            ts=r["target_timestamp"]; slices[("hour",str(ts.hour))].append(r);slices[("month",str(ts.month))].append(r)
            group="low_output" if r["actual"]<=q1 else "high_output" if r["actual"]>=q3 else "middle_output";slices[("output_quartile",group)].append(r)
            if key[0]=="load" and r["actual"]>=q3:slices[("target_condition","higher_demand_q4")].append(r)
            if key[0]=="wind": slices[("target_condition","low_generation_q1" if r["actual"]<=q1 else "high_generation_q4" if r["actual"]>=q3 else "middle_generation")].append(r)
            if key[0]=="pv": slices[("target_condition","nighttime_zero" if r["actual"]==0 else "low_output_q1" if r["actual"]<=q1 else "high_output_q4" if r["actual"]>=q3 else "middle_output")].append(r)
        for (dimension,label),items in slices.items(): out.append({"target":key[0],"horizon":key[1],"model":key[2],"dimension":dimension,"slice":label,"samples":len(items),"MAE":sum(x["absolute_error"] for x in items)/len(items)})
    path=ROOT/"artifacts/experiments/classical/phase_07/diagnostics/error_slices.csv";write(path,out)
    manifest_path=ROOT/"artifacts/experiments/classical/phase_07/classical_experiment_manifest.yaml";manifest=json.loads(manifest_path.read_text());manifest["artifact_checksums"][str(path.relative_to(ROOT))]=hashlib.sha256(path.read_bytes()).hexdigest();manifest_path.write_text(json.dumps(manifest,indent=2)+"\n");(ROOT/"artifacts/experiments/classical/phase_07/manifests/classical_experiment_manifest.yaml").write_text(json.dumps(manifest,indent=2)+"\n")
log.info(f'Wrote {len(out)} descriptive error slices; final test not accessed.')
if __name__=="__main__":main()
