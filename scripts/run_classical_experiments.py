#!/usr/bin/env python3
"""Phase 7 fixed-config, rolling-origin, validation-only classical experiments."""
from __future__ import annotations

import argparse, csv, hashlib, json, platform, subprocess, sys, time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "src"))
from smartgrid_mlops.experimental_design.metrics import mae, rmse, smape, nmae, nrmse
from smartgrid_mlops.experimental_design.rolling_origin import fold_boundaries
from smartgrid_mlops.models.factory import create_model, is_stochastic, load_config, specification
from smartgrid_mlops.models.validation import reject_final_test
import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stderr,
)
LOGGER = logging.getLogger(__name__)

FEATURES=["hour_sin","hour_cos","dow_sin","dow_cos","doy_sin","doy_cos","lag_1","lag_24","lag_168","rolling_mean_24","rolling_mean_168","ramp_1h"]
MODELS=("linear_regression","ridge","random_forest","extra_trees","hist_gradient_boosting")
SEEDS=(42,123,2020,2025,31415)
TARGET_COLUMNS={"load":("load_hourly.parquet","actual_system_load"),"wind":("wind_hourly.parquet","actual_wind"),"pv":("pv_hourly.parquet","actual_pv")}
METRICS=("MAE","RMSE","sMAPE","nMAE","nRMSE")

def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def metric(rows):
    a,p=[r["actual"] for r in rows],[r["prediction"] for r in rows]
    return {"MAE":mae(a,p),"RMSE":rmse(a,p),"sMAPE":smape(a,p),"nMAE":nmae(a,p),"nRMSE":nrmse(a,p)}
def csv_write(path, rows, fields):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("w",newline="",encoding="utf-8") as s: w=csv.DictWriter(s,fieldnames=fields);w.writeheader();w.writerows(rows)
def markdown(path,title,rows,fields,note):
    path.parent.mkdir(parents=True,exist_ok=True)
    def v(x): return f"{x:.6f}" if isinstance(x,float) else str(x)
    path.write_text(f"# {title}\n\n**{note}**\n\n| "+" | ".join(fields)+" |\n| "+" | ".join(["---"]*len(fields))+" |\n"+"".join("| "+" | ".join(v(r[f]) for f in fields)+" |\n" for r in rows),encoding="utf-8")

def feature_rows(target,horizon):
    path=ROOT/f"data/processed/features/{target}/h{horizon}/combined_v1.parquet"
    return pq.read_table(path,columns=["forecast_origin","target_timestamp",*FEATURES]).to_pylist()
def actual_map(target):
    filename,column=TARGET_COLUMNS[target]; rows=pq.read_table(ROOT/"data/processed"/filename,columns=["timestamp",column]).to_pylist()
    return {r["timestamp"]:float(r[column]) for r in rows}
def baseline_references():
    rows=list(csv.DictReader((ROOT/"artifacts/research_tables/baseline_validation_results.csv").open()))
    refs={}
    for r in rows:
        key=(r["target"],int(r["horizon"])); value=float(r["MAE"])
        if r["external_baseline"]=="False":
            if key not in refs or value<refs[key][1]: refs[key]=(r["baseline"],value)
        if int(r["horizon"])==24 and r["baseline"]=="RTS_DAY_AHEAD": refs[key+('external',)]=(r["baseline"],value)
    return refs
def complexity(model):
    if hasattr(model,"named_steps"): model=model.named_steps.get("ridge",model)
    if hasattr(model,"coef_"): return {"coefficient_count":len(model.coef_)}
    if hasattr(model,"estimators_"):
        depths=[e.tree_.max_depth for e in model.estimators_];return {"estimator_count":len(depths),"mean_tree_depth":sum(depths)/len(depths),"max_tree_depth":max(depths)}
    if hasattr(model,"n_iter_"): return {"iterations":int(model.n_iter_)}
    return {}

def run(targets=("load","wind","pv"), horizons=(1,24), models=MODELS, smoke=False):
    config=load_config(); refs=baseline_references(); all_predictions=[]; run_meta=[]
    for target in targets:
      actual=actual_map(target)
      for horizon in horizons:
        rows=feature_rows(target,horizon)
        for boundary in fold_boundaries():
          train=[r for r in rows if boundary["training_start"]<=r["target_timestamp"]<boundary["training_end_exclusive"]]
          valid=[r for r in rows if boundary["validation_start"]<=r["target_timestamp"]<boundary["validation_end_exclusive"]]
          for r in valid: reject_final_test(r["target_timestamp"])
          xtrain=[[r[f] for f in FEATURES] for r in train]; ytrain=[actual[r["target_timestamp"]] for r in train]
          xvalid=[[r[f] for f in FEATURES] for r in valid]; yvalid=[actual[r["target_timestamp"]] for r in valid]
          for family in models:
            seeds=(SEEDS if is_stochastic(family) and not smoke else (SEEDS[:1] if is_stochastic(family) else (None,)))
            for seed in seeds:
              model=create_model(family,seed,config); start=time.perf_counter();model.fit(xtrain,ytrain); train_time=time.perf_counter()-start;start=time.perf_counter();pred=model.predict(xvalid);pred_time=time.perf_counter()-start
              neg=sum(value<0 for value in pred); ref=refs[(target,horizon)]
              exp=f"{target.upper()}-H{horizon}-{family.upper()}-FULLV1-{'S'+str(seed) if seed is not None else 'DET'}-{boundary['fold_id']}"
              for source,value,actual_value in zip(valid,pred,yvalid): all_predictions.append({"experiment_id":exp,"target":target,"horizon":horizon,"model_family":family,"feature_set":"combined_v1","fold_id":boundary["fold_id"],"seed":seed,"forecast_origin":source["forecast_origin"],"target_timestamp":source["target_timestamp"],"actual":actual_value,"prediction":float(value),"error":float(actual_value-value),"absolute_error":abs(float(actual_value-value)),"squared_error":float((actual_value-value)**2),"baseline_reference":ref[0]})
              run_meta.append({"experiment_id":exp,"target":target,"horizon":horizon,"model":family,"fold":boundary["fold_id"],"seed":"DET" if seed is None else seed,"train_samples":len(train),"validation_samples":len(valid),"training_seconds":train_time,"prediction_seconds":pred_time,"negative_prediction_count":neg,"negative_prediction_percentage":100*neg/len(pred),"complexity":json.dumps(complexity(model),sort_keys=True),"hyperparameters":json.dumps(config["models"][family],sort_keys=True)})
    output=ROOT/"artifacts/experiments/classical/phase_07"; (output/"predictions").mkdir(parents=True,exist_ok=True);pq.write_table(pa.Table.from_pylist(all_predictions),output/"predictions/classical_predictions.parquet")
    csv_write(output/"metrics/run_metadata.csv",run_meta,list(run_meta[0]))
    # Seed summaries: mean prediction per timestamp, yielding one fair row per fold/model.
    grouped=defaultdict(list)
    for r in all_predictions: grouped[(r["target"],r["horizon"],r["model_family"],r["fold_id"],r["target_timestamp"])].append(r)
    seedmean=[]
    for values in grouped.values():
        base=values[0].copy(); base["prediction"]=sum(x["prediction"] for x in values)/len(values); base["error"]=base["actual"]-base["prediction"];base["absolute_error"]=abs(base["error"]);base["squared_error"]=base["error"]**2;seedmean.append(base)
    fold=[]
    for key in sorted({(r["target"],r["horizon"],r["model_family"],r["fold_id"]) for r in seedmean}):
        values=[r for r in seedmean if (r["target"],r["horizon"],r["model_family"],r["fold_id"])==key];fold.append({"target":key[0],"horizon":key[1],"model":key[2],"fold":key[3],"seed_summary":"mean_prediction_across_predefined_seeds" if is_stochastic(key[2]) else "deterministic","samples":len(values),**metric(values)})
    aggregate=[]
    for key in sorted({(r["target"],r["horizon"],r["model_family"]) for r in seedmean}):
        values=[r for r in seedmean if (r["target"],r["horizon"],r["model_family"])==key and r["target_timestamp"]>=datetime(2020,9,1)];m=metric(values); ref=refs[(key[0],key[1])]
        aggregate.append({"target":key[0],"horizon":key[1],"model":key[2],"feature_set":"combined_v1","samples":len(values),**m,"best_baseline":ref[0],"best_baseline_MAE":ref[1],"relative_MAE_difference_pct":100*(ref[1]-m["MAE"])/ref[1],"rts_day_ahead_MAE":refs.get((key[0],key[1],"external"),(None,None))[1]})
    seed_stability=[]
    for key in sorted({(r["target"],r["horizon"],r["model_family"],r["fold_id"],r["seed"]) for r in all_predictions if r["seed"] is not None}):
        vals=[r for r in all_predictions if (r["target"],r["horizon"],r["model_family"],r["fold_id"],r["seed"])==key];seed_stability.append({"target":key[0],"horizon":key[1],"model":key[2],"fold":key[3],"seed":key[4],"MAE":metric(vals)["MAE"]})
    fields=["target","horizon","model","feature_set","samples",*METRICS,"best_baseline","best_baseline_MAE","relative_MAE_difference_pct","rts_day_ahead_MAE"]
    tables=ROOT/"artifacts/research_tables";reports=ROOT/"reports/tables";csv_write(tables/"classical_h24_validation_results.csv",[r for r in aggregate if r["horizon"]==24],fields);csv_write(tables/"classical_h1_validation_results.csv",[r for r in aggregate if r["horizon"]==1],fields);csv_write(tables/"classical_fold_results.csv",fold,list(fold[0]));csv_write(tables/"classical_seed_stability.csv",seed_stability,list(seed_stability[0]));markdown(reports/"classical_h24_validation_results.md","Classical H24 validation results",[r for r in aggregate if r["horizon"]==24],fields,"Validation only; final test not accessed.");markdown(reports/"classical_h1_validation_results.md","Classical H1 validation results",[r for r in aggregate if r["horizon"]==1],fields,"Secondary validation results only; final test not accessed.")
    runtime_fields=["target","horizon","model","fold","seed","training_seconds","prediction_seconds"]; markdown(reports/"classical_runtime_comparison.md","Classical runtime comparison",[{k:r[k] for k in runtime_fields} for r in run_meta],runtime_fields,"Measured on this execution environment; not hardware-independent.")
    diagnostics=[]
    for key in sorted({(r["target"],r["horizon"],r["model_family"]) for r in seedmean}):
        vals=[r for r in seedmean if (r["target"],r["horizon"],r["model_family"])==key];diagnostics.append({"target":key[0],"horizon":key[1],"model":key[2],"negative_prediction_count":sum(r["prediction"]<0 for r in vals),"negative_prediction_percentage":100*sum(r["prediction"]<0 for r in vals)/len(vals),"prediction_above_observed_max_count":sum(r["prediction"]>max(x["actual"] for x in vals) for r in vals)})
    csv_write(output/"diagnostics/physical_validity.csv",diagnostics,list(diagnostics[0]));csv_write(output/"metrics/fold_metrics.csv",fold,list(fold[0]));csv_write(output/"metrics/aggregate_metrics.csv",aggregate,fields);csv_write(output/"metrics/seed_stability.csv",seed_stability,list(seed_stability[0]))
    from smartgrid_mlops.data_audit.reporting import _write_png
    figs=ROOT/"artifacts/research_figures/phase_07";figs.mkdir(parents=True,exist_ok=True); figures=[]
    for filename,vals in (("classical_h24_mae_comparison.png",[r["MAE"] for r in aggregate if r["horizon"]==24]),("classical_h24_rmse_comparison.png",[r["RMSE"] for r in aggregate if r["horizon"]==24]),("fold_stability_classical.png",[r["MAE"] for r in fold])):
        p=figs/filename;_write_png(p,vals,filename);figures.append(p)
    for target in targets:
        p=figs/f"{target}_model_comparison.png";_write_png(p,[r["MAE"] for r in aggregate if r["target"]==target and r["horizon"]==24],p.name);figures.append(p)
    fig_manifest=[{"figure_id":f"FIG-ML-{i:03d}","title":p.stem,"models":list(models),"target":"multiple" if "classical" in p.name or "fold" in p.name else p.stem.split("_")[0],"horizon":24 if "h24" in p.name or "model" in p.name else "multiple","evaluation_partition":"validation only; final test excluded","source_artifact":"artifacts/experiments/classical/phase_07/metrics","generation_script":"scripts/run_classical_experiments.py","paper_relevance":"Untuned classical validation comparison"} for i,p in enumerate(figures,1)]
    (figs/"figure_manifest.yaml").write_text(json.dumps(fig_manifest,indent=2)+"\n")
    p7=ROOT/"artifacts/experimental_design/phase_07_model_protocol_freeze.yaml"; protocol=ROOT/"artifacts/experimental_design/protocol_freeze.yaml";feature=ROOT/"data/manifests/feature_manifest.yaml"
    try: commit=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True,stderr=subprocess.DEVNULL).strip()
    except Exception: commit="unknown"
    artifact_paths=[output/"predictions/classical_predictions.parquet",output/"metrics/aggregate_metrics.csv",output/"metrics/fold_metrics.csv",output/"metrics/seed_stability.csv",output/"diagnostics/physical_validity.csv",figs/"figure_manifest.yaml"]
    manifest={"phase":"07","final_test_accessed":False,"protocol_checksum":digest(protocol),"phase_07_model_protocol_checksum":digest(p7),"feature_manifest_checksum":digest(feature),"config_checksum":digest(ROOT/"config/models/classical_untuned_v1.yaml"),"dataset_version":"rts_gmlc_processed_v1","feature_set":"combined_v1","code_commit":commit,"environment":{"platform":platform.platform(),"python":sys.version.split()[0]},"artifact_checksums":{str(p.relative_to(ROOT)):digest(p) for p in artifact_paths}}
    (output/"manifests").mkdir(parents=True,exist_ok=True);(output/"classical_experiment_manifest.yaml").write_text(json.dumps(manifest,indent=2)+"\n");(output/"manifests/classical_experiment_manifest.yaml").write_text(json.dumps(manifest,indent=2)+"\n")
    return {"runs":len(run_meta),"predictions":len(all_predictions),"aggregate":aggregate,"diagnostics":diagnostics}

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--all",action="store_true");p.add_argument("--target",action="append",choices=("load","wind","pv"));p.add_argument("--horizon",action="append",type=int,choices=(1,24));p.add_argument("--model",action="append",choices=MODELS);p.add_argument("--smoke",action="store_true");a=p.parse_args()
    if not (a.all or a.target or a.horizon or a.model):p.error("specify --all or a scoped selection")
    result=run(tuple(a.target or ("load","wind","pv")),tuple(a.horizon or (1,24)),tuple(a.model or MODELS),a.smoke);print(json.dumps({"final_test_accessed":False,"runs":result["runs"],"prediction_rows":result["predictions"]},indent=2))
