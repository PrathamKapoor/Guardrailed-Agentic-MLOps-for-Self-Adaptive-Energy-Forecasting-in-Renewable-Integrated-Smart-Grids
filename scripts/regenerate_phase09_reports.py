#!/usr/bin/env python3
"""Regenerate Phase 9 derived reports from stored evidence only.

This script intentionally uses sqlite3 rather than Optuna's API and never
imports a training runner.  It is safe for evidence aggregation and cannot
start optimisation or post-HPO evaluation.
"""
from __future__ import annotations

import csv, hashlib, json, math, sqlite3, statistics
from pathlib import Path
import sys

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from smartgrid_mlops.reporting.phase09_evidence import select_official_evidence
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stderr,
)
LOGGER = logging.getLogger(__name__)

PHASE = ROOT / "artifacts/experiments/hpo/phase_09"
TABLES = ROOT / "artifacts/research_tables"
REPORT_TABLES = ROOT / "reports/tables"
FIGURES = ROOT / "artifacts/research_figures/phase_09"
TARGETS = ("load", "wind", "pv")
CLASSICAL = {"load": ("random_forest", "load_random_forest.db"), "wind": ("hist_gradient_boosting", "wind_hist_gradient_boosting.db"), "pv": ("random_forest", "pv_random_forest.db")}
NEURAL = {target: f"{target}_pytorch_mlp_v1_recovery.db" for target in TARGETS}

def read_csv(path):
    with path.open(newline="") as f: return list(csv.DictReader(f))
def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else [])
        writer.writeheader(); writer.writerows(rows)
def mean(xs): return statistics.mean(xs) if xs else None
def fmt(x): return "N/A" if x is None else f"{float(x):.3f}"
def md(path, title, headers, rows, note=""):
    path.parent.mkdir(parents=True, exist_ok=True)
    lines=[f"# {title}", "", "| " + " | ".join(headers) + " |", "| " + " | ".join(["---"]*len(headers)) + " |"]
    lines += ["| " + " | ".join(str(r.get(h, "N/A")) for h in headers) + " |" for r in rows]
    if note: lines += ["", note]
    path.write_text("\n".join(lines)+"\n", encoding="utf-8")

def decode_param(value, distribution):
    d=json.loads(distribution)
    if d.get("name") == "CategoricalDistribution": return d["attributes"]["choices"][int(value)]
    return value
def db_trials(db_path, target, model, framework, implementation_id, status, deviation_id=""):
    con=sqlite3.connect(db_path); con.row_factory=sqlite3.Row
    study=con.execute("select study_name from studies limit 1").fetchone()[0]
    records=[]
    for trial in con.execute("select trial_id, number, state from trials order by number"):
        params={r["param_name"]: decode_param(r["param_value"], r["distribution_json"]) for r in con.execute("select param_name,param_value,distribution_json from trial_params where trial_id=?", (trial["trial_id"],))}
        value=con.execute("select value from trial_values where trial_id=? order by objective", (trial["trial_id"],)).fetchone()
        attrs={r["key"]: json.loads(r["value_json"]) for r in con.execute("select key,value_json from trial_user_attributes where trial_id=?", (trial["trial_id"],))}
        records.append({"study_id":study,"trial_id":trial["number"],"target":target,"model":model,"framework":framework,"implementation_id":implementation_id,"evidence_status":status,"deviation_id":deviation_id,"objective_MAE":value[0] if value else None,"runtime":attrs.get("runtime_seconds", attrs.get("runtime")),"trial_status":trial["state"],"hyperparameters":json.dumps(params,sort_keys=True),"fold_MAE":json.dumps(attrs.get("fold_mae",[]))})
    return records
def evidence_records():
    records=[]
    for target,(model,db) in CLASSICAL.items(): records += db_trials(PHASE/"studies"/db,target,model,"sklearn",model.upper(),"VALID")
    for target,db in NEURAL.items(): records += db_trials(PHASE/"studies"/db,target,"mlp","pytorch","PYTORCH_MLP_V1","VALID")
    for target in TARGETS: records += db_trials(PHASE/"invalid_neural_sklearn"/f"{target}_mlp.db",target,"mlp","sklearn","MLPRegressor","INVALIDATED","P9-DEV-001")
    return records
def selected(records, target, model):
    return min((r for r in records if r["target"]==target and r["model"]==model and r["objective_MAE"] is not None), key=lambda r:r["objective_MAE"])
def baseline_map():
    out={}
    for r in read_csv(TABLES/"baseline_validation_results.csv"):
        if r["horizon"]=="24": out[(r["target"],r["baseline"])]=float(r["MAE"])
    return out
def phase8_matched():
    post=read_csv(PHASE/"post_hpo_validation/predictions.csv")
    wanted={(r["target"],r["fold"],int(r["seed"]),r["target_timestamp"]) for r in post}
    raw=pq.read_table(ROOT/"artifacts/experiments/neural/phase_08/predictions/neural_predictions.parquet").to_pylist()
    groups={t:[] for t in TARGETS}
    for r in raw:
        key=(r["target"],r["fold"],r["seed"],str(r["target_timestamp"]))
        if r["model"]=="mlp" and r["horizon"]==24 and r["fold"] in ("F05","F06") and key in wanted: groups[r["target"]].append(abs(float(r["error"])))
    return {t:mean(v) for t,v in groups.items()}
def post_summary():
    metrics=read_csv(PHASE/"post_hpo_validation/metrics.csv")
    good,rejected=select_official_evidence([{**r,"evidence_status":"VALID"} for r in metrics], neural_only=True)
    if rejected: raise RuntimeError(f"unexpected post-HPO rejection: {rejected}")
    groups=[]
    for target in TARGETS:
        for fold in ("F05","F06"):
            rows=[r for r in good if r["target"]==target and r["fold"]==fold]
            if len(rows)!=5: raise RuntimeError(f"{target} {fold} has {len(rows)} valid runs; expected 5")
            vals=lambda k:[float(r[k]) for r in rows]
            groups.append({"target":target,"fold":fold,"runs":len(rows),"mean_MAE":mean(vals("MAE")),"std_MAE":statistics.stdev(vals("MAE")),"min_MAE":min(vals("MAE")),"max_MAE":max(vals("MAE")),"mean_RMSE":mean(vals("RMSE")),"std_RMSE":statistics.stdev(vals("RMSE")),"mean_sMAPE":mean(vals("sMAPE")),"mean_nMAE":mean(vals("nMAE")),"mean_nRMSE":mean(vals("nRMSE")),"fold_training_seconds":sum(vals("training_seconds"))})
    target_summary={t:mean([r["mean_MAE"] for r in groups if r["target"]==t]) for t in TARGETS}
    return metrics,groups,target_summary
def physical_summary():
    rows=read_csv(PHASE/"post_hpo_validation/predictions.csv"); out=[]
    for t in TARGETS:
        vals=[float(r["prediction"]) for r in rows if r["target"]==t]
        out.append({"target":t,"predictions":len(vals),"negative_prediction_count":sum(v<0 for v in vals),"negative_prediction_percentage":100*sum(v<0 for v in vals)/len(vals),"NaN_count":sum(math.isnan(v) for v in vals),"Inf_count":sum(math.isinf(v) for v in vals)})
    return out
def figures(records, validation):
    FIGURES.mkdir(parents=True, exist_ok=True)
    def svg(path, title, points, x_label, y_label):
        # Dependency-free SVG is deliberate: reporting must work in the locked venv.
        width,height,pad=760,420,70
        xs=[p[0] for p in points] or [0]; ys=[p[1] for p in points] or [0]
        xmin,xmax=min(xs),max(xs); ymin,ymax=min(ys),max(ys)
        if xmin==xmax: xmax=xmin+1
        if ymin==ymax: ymax=ymin+1
        xy=[(pad+(x-xmin)/(xmax-xmin)*(width-2*pad),height-pad-(y-ymin)/(ymax-ymin)*(height-2*pad)) for x,y in points]
        poly=" ".join(f"{x:.1f},{y:.1f}" for x,y in xy)
        circles="".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="#2563eb"/>' for x,y in xy)
        path.write_text(f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}"><rect width="100%" height="100%" fill="white"/><text x="{width/2}" y="28" text-anchor="middle" font-size="18">{title}</text><line x1="{pad}" y1="{height-pad}" x2="{width-pad}" y2="{height-pad}" stroke="black"/><line x1="{pad}" y1="{pad}" x2="{pad}" y2="{height-pad}" stroke="black"/><polyline points="{poly}" fill="none" stroke="#2563eb" stroke-width="2"/>{circles}<text x="{width/2}" y="{height-18}" text-anchor="middle">{x_label}</text><text x="20" y="{height/2}" transform="rotate(-90 20 {height/2})" text-anchor="middle">{y_label}</text></svg>''',encoding="utf-8")
    neural,_=select_official_evidence(records,neural_only=True)
    for t in TARGETS:
        vals=sorted([r for r in neural if r["target"]==t and r["objective_MAE"] is not None],key=lambda r:r["trial_id"])
        best=[]; running=float("inf")
        for r in vals: running=min(running,r["objective_MAE"]); best.append(running)
        svg(FIGURES/f"pytorch_hpo_history_{t}.svg",f"Valid PyTorch HPO history: {t} H24",list(zip([r["trial_id"] for r in vals],best)),"Trial number","Best-so-far MAE")
    labels=[r["Target"] for r in validation]; values=[float(r["Post-HPO MAE F05-F06"]) if r["Post-HPO MAE F05-F06"]!="N/A" else float(r["Search MAE F01-F04"]) for r in validation]
    svg(FIGURES/"hpo_improvement_by_target.svg","Valid Phase 9 HPO evidence",list(enumerate(values)),"Validated candidate index","MAE")
    svg(FIGURES/"hpo_runtime_vs_improvement.svg","Valid HPO runtime versus improvement",[(float(r["Runtime seconds"]),float(r["Relative tuning improvement %"]) if r["Relative tuning improvement %"]!="N/A" else 0) for r in validation],"Valid search runtime (s)","Relative tuning improvement (%)")
    neural_rows=[r for r in validation if r["Model"] == "Tuned PyTorch MLP"]
    svg(FIGURES/"untuned_vs_tuned_h24.svg","Matched untuned versus tuned PyTorch H24",[(i,float(r["Untuned MAE"])) for i,r in enumerate(neural_rows)]+[(i+0.25,float(r["Post-HPO MAE F05-F06"])) for i,r in enumerate(neural_rows)],"Target index (untuned, tuned)","MAE")
    svg(FIGURES/"model_evolution_h24.svg","H24 valid model-evolution summary",list(enumerate(values)),"Validated candidate index","MAE")
def main():
    records=evidence_records(); official,rejected=select_official_evidence(records)
    write_csv(TABLES/"hpo_trial_history.csv",official)
    write_csv(TABLES/"hpo_trial_history_audit.csv",records)
    metrics,seed_rows,post=post_summary(); write_csv(TABLES/"hpo_post_hpo_seed_stability.csv",seed_rows)
    bases=baseline_map(); matched=phase8_matched(); validation=[]
    for target in TARGETS:
        c=selected(official,target,CLASSICAL[target][0]); n=selected(official,target,"mlp")
        untuned_classical=min(float(r["MAE"]) for r in read_csv(TABLES/"classical_h24_validation_results.csv") if r["target"]==target)
        naive_name="H24_DAILY_PERSISTENCE"; naive=bases[(target,naive_name)]; rts=bases[(target,"RTS_DAY_AHEAD")]
        for label,record,untuned,post_value in (("Tuned classical",c,untuned_classical,None),("Tuned PyTorch MLP",n,matched[target],post[target])):
            improvement=(untuned-post_value)/untuned*100 if post_value is not None else (untuned-record["objective_MAE"])/untuned*100
            validation.append({"Target":target,"Model":label,"Framework":record["framework"],"Implementation ID":record["implementation_id"],"Untuned MAE":fmt(untuned),"Search MAE F01-F04":fmt(record["objective_MAE"]),"Post-HPO MAE F05-F06":fmt(post_value),"Relative tuning improvement %":fmt(improvement),"Best naive baseline MAE":fmt(naive),"RTS DAY_AHEAD MAE":fmt(rts),"Trials":sum(1 for r in official if r["study_id"]==record["study_id"]),"Runtime seconds":fmt(sum(float(r["runtime"] or 0) for r in official if r["study_id"]==record["study_id"]))})
    write_csv(TABLES/"hpo_validation_results.csv",validation); md(REPORT_TABLES/"hpo_validation_results.md","Phase 9 HPO validation results",list(validation[0]),validation,"Search MAE is F01–F04; Post-HPO MAE is the mean of F05/F06 fold mean MAEs. Within-fold seed standard deviations are reported separately in `hpo_post_hpo_seed_stability.csv`.")
    params=[]
    for cfg in sorted((PHASE/"best_configs").glob("*_pytorch_mlp.yaml")):
        d=json.loads(cfg.read_text()); params.append({"target":d["target"],"model":d["model_family"],"framework":d["framework"],"implementation_id":d["implementation_id"],"selected_trial_id":d["selected_trial_id"],"search_MAE":fmt(d["search_MAE"]),"hyperparameters":json.dumps(d["hyperparameters"],sort_keys=True),"config SHA-256":hashlib.sha256(cfg.read_bytes()).hexdigest()})
    md(REPORT_TABLES/"hpo_best_parameters.md","Frozen valid PyTorch HPO parameters",list(params[0]),params)
    costs=[]
    cost_groups = (
        ("VALID classical HPO search", [r for r in official if r["framework"] == "sklearn"]),
        ("VALID PyTorch HPO search", [r for r in official if r["framework"] == "pytorch"]),
        ("PyTorch post-HPO evaluation", [{"runtime": r["training_seconds"]} for r in metrics]),
        ("INVALIDATED / AUDIT-ONLY COMPUTE", [r for r in records if r["evidence_status"] == "INVALIDATED"]),
    )
    for label,subset in cost_groups:
        costs.append({"Evidence":label,"Runs":len(subset),"Runtime seconds":fmt(sum(float(r["runtime"] or 0) for r in subset)),"Official": "YES" if label.startswith("VALID") or label.startswith("PyTorch post") else "NO"})
    md(REPORT_TABLES/"hpo_computational_cost.md","Phase 9 computational cost",list(costs[0]),costs)
    evol=[]
    for t in TARGETS:
        c=next(r for r in validation if r["Target"]==t and r["Model"]=="Tuned classical"); n=next(r for r in validation if r["Target"]==t and r["Model"]=="Tuned PyTorch MLP")
        evol += [{"Target":t,"Evidence": "daily persistence" if t=="pv" else "best naive","Role":"benchmark","MAE":c["Best naive baseline MAE"]},{"Target":t,"Evidence":"RTS DAY_AHEAD","Role":"benchmark","MAE":c["RTS DAY_AHEAD MAE"]},{"Target":t,"Evidence":"untuned classical","Role":"F01-F06 retrospective","MAE":c["Untuned MAE"]},{"Target":t,"Evidence":"tuned classical","Role":"SEARCH F01-F04","MAE":c["Search MAE F01-F04"]},{"Target":t,"Evidence":"untuned PyTorch MLP","Role":"matched F05-F06","MAE":n["Untuned MAE"]},{"Target":t,"Evidence":"tuned PyTorch MLP","Role":"POST-HPO F05-F06","MAE":n["Post-HPO MAE F05-F06"]}]
    md(REPORT_TABLES/"model_evolution_h24.md","H24 model evolution",list(evol[0]),evol,"Search and post-HPO evaluation roles are intentionally not conflated.")
    physical=physical_summary(); write_csv(TABLES/"hpo_post_hpo_physical_validity.csv",physical)
    figures(official,validation)
    manifest={"phase":"09","policy":"VALID only; neural additionally requires pytorch/PYTORCH_MLP_V1","figures":[{"figure_id":p.stem,"source_evidence":"VALID Phase 9 trial or validation evidence","evidence_status":"VALID","target":next((t for t in TARGETS if t in p.stem),"all"),"evaluation_role":"SEARCH F01-F04" if "history" in p.stem else "POST-HPO/summary","generation_script":"scripts/regenerate_phase09_reports.py","paper_relevance":"HPO reporting"} for p in sorted(FIGURES.glob("*.svg"))]}
    (FIGURES/"figure_manifest.yaml").write_text(json.dumps(manifest,indent=2)+"\n")
    summary={"official_trial_records":len(official),"rejected_trial_records":len(rejected),"post_hpo_runs":len(metrics),"post_hpo_target_mae":post,"matched_untuned_pytorch_mae":matched,"physical_validity":physical,"invalid_official_evidence":0,"costs":costs}
    (TABLES/"phase09_reporting_summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    print(json.dumps(summary,indent=2))
if __name__ == "__main__": main()
