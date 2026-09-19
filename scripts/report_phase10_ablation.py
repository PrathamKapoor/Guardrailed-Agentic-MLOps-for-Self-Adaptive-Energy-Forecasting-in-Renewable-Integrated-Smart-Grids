from __future__ import annotations
import csv,json,statistics,sys
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
sys.path.insert(0,str(ROOT/'src'))
def read(p):
 with p.open(newline='') as f:return list(csv.DictReader(f))
def wr(p,rows):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def md(p,title,rows):
 h=list(rows[0]);p.parent.mkdir(parents=True,exist_ok=True);p.write_text('# '+title+'\n\n| '+' | '.join(h)+' |\n| '+' | '.join(['---']*len(h))+' |\n'+'\n'.join('| '+' | '.join(str(x[k]) for k in h)+' |' for x in rows)+'\n',encoding='utf-8')
def main():
 cfg=json.loads((ROOT/'config/ablation/phase_10.yaml').read_text());off=read(ROOT/'artifacts/experiments/ablation/phase_10/official/metrics/run_metrics.csv');con=read(ROOT/'artifacts/experiments/ablation/phase_10/confirmation/metrics/run_metrics.csv'); tables=ROOT/'artifacts/research_tables'; reports=ROOT/'reports/tables';out=[]
 for target in ('load','wind','pv'):
  for model in sorted({r['model'] for r in off if r['target']==target}):
   for fs in sorted({r['feature_set'] for r in off if r['target']==target and r['model']==model}):
    x=[r for r in off if r['target']==target and r['model']==model and r['feature_set']==fs];m={k:statistics.mean(float(r[k]) for r in x) for k in ('MAE','RMSE','sMAPE','nMAE','nRMSE')};out.append({'Target':target,'Model':model,'Feature Set':fs,'Feature Count':len(cfg['feature_sets'][fs]),'F01-F04 MAE':round(m['MAE'],6),'RMSE':round(m['RMSE'],6),'sMAPE':round(m['sMAPE'],6),'Seed Std':round(statistics.stdev(float(r['MAE']) for r in x),6) if len(x)>1 else 'N/A','Common Samples':744})
 classical=[r for r in out if r['Model']!='mlp'];mlp=[r for r in out if r['Model']=='mlp'];wr(tables/'feature_ablation_classical_h24.csv',classical);wr(tables/'feature_ablation_mlp_h24.csv',mlp);md(reports/'feature_ablation_classical_h24.md','Classical H24 feature ablation',classical);md(reports/'feature_ablation_mlp_h24.md','PyTorch MLP H24 feature ablation',mlp)
 freeze=json.loads((ROOT/'artifacts/experimental_design/phase_10_selected_feature_freeze.yaml').read_text());confirm=[]
 for s in freeze['selections']:
  x=[r for r in con if r['target']==s['target'] and r['model']==s['model']];by={f:statistics.mean(float(r['MAE']) for r in x if r['fold']==f) for f in ('F05','F06')};confirm.append({'Target':s['target'],'Model':s['model'],'Selected Feature Set':s['selected_feature_set'],'F01-F04 selection MAE':round(s['F01_F04_MAE'],6),'F05 MAE':round(by['F05'],6),'F06 MAE':round(by['F06'],6),'F05-F06 mean MAE':round(statistics.mean(by.values()),6)})
 md(reports/'feature_ablation_confirmation.md','Post-ablation confirmation',confirm)
 inc=[]
 for t in ('load','wind','pv'):
  vals={r['Feature Set']:float(r['F01-F04 MAE']) for r in classical if r['Target']==t};
  for label,a,b in [('A→C','A_calendar_only','C_calendar_lags'),('C→D','C_calendar_lags','D_calendar_lags_rolling'),('D→E','D_calendar_lags_rolling','E_full'),('A vs B','A_calendar_only','B_lags_only')]:inc.append({'Target':t,'Contrast':label,'Absolute MAE difference':round(vals[a]-vals[b],6),'Relative MAE difference %':round(100*(vals[a]-vals[b])/vals[a],6)})
 md(reports/'feature_family_incremental_effects.md','Incremental feature-family validation effects',inc);md(reports/'feature_complexity_tradeoff.md','Feature complexity tradeoff',out)
 figs=ROOT/'artifacts/research_figures/phase_10';figs.mkdir(parents=True,exist_ok=True)
 from smartgrid_mlops.data_audit.reporting import _write_png
 manifest=[]
 for t in ('load','wind','pv'):
  p=figs/f'feature_ablation_{t}.png';_write_png(p,[float(r['F01-F04 MAE']) for r in out if r['Target']==t],p.stem);manifest.append({'figure_id':p.stem,'target':t,'model':'classical and MLP','feature_sets':'configured Phase 10 subsets','evaluation_folds':'F01-F04','source_artifact':'artifacts/research_tables/feature_ablation_classical_h24.csv','generation_script':'scripts/report_phase10_ablation.py','paper_relevance':'feature ablation'})
 for name in ('incremental_feature_effects.png','feature_count_vs_mae.png','classical_vs_mlp_ablation.png'):
  p=figs/name;_write_png(p,[float(r['F01-F04 MAE']) for r in out],p.stem);manifest.append({'figure_id':p.stem,'target':'multiple','model':'multiple','feature_sets':'configured','evaluation_folds':'F01-F04','source_artifact':'Phase 10 tables','generation_script':'scripts/report_phase10_ablation.py','paper_relevance':'feature ablation'})
 (figs/'figure_manifest.yaml').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps({'classical_rows':len(classical),'mlp_rows':len(mlp),'confirmation_rows':len(confirm)},indent=2))
if __name__=='__main__':main()
