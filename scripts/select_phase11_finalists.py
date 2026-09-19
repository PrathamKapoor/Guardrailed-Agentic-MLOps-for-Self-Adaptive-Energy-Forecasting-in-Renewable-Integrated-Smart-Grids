from __future__ import annotations
import csv,hashlib,json,math,statistics,sys
from collections import defaultdict
from pathlib import Path
import pyarrow.parquet as pq
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from smartgrid_mlops.finalists.selection import choose_reference,holm
import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stderr,
)
LOGGER = logging.getLogger(__name__)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def mae(rows):return statistics.mean(float(x['absolute_error']) for x in rows)
def main():
 out=ROOT/'artifacts/research_tables';out.mkdir(parents=True,exist_ok=True); ab=pq.read_table(ROOT/'artifacts/experiments/ablation/phase_10/confirmation/predictions/predictions.parquet').to_pylist(); base=pq.read_table(ROOT/'artifacts/experiments/baselines/phase_06/predictions/baseline_predictions.parquet').to_pylist(); selected=[]; baselines={'load':'RTS_DAY_AHEAD','wind':'RTS_DAY_AHEAD','pv':'H24_DAILY_PERSISTENCE'}; comparisons=[]; registry={}
 for target in ('load','wind','pv'):
  candidates=[]
  for model,fs,complexity in [('random_forest' if target!='wind' else 'hist_gradient_boosting','B_lags_only',3),('mlp','E_full',12)]:
   rows=[r for r in ab if r['target']==target and r['model']==model and r['feature_set']==fs];g=defaultdict(list)
   for r in rows:g[r['target_timestamp']].append(r)
   meanrows=[]
   for v in g.values():
    x=v[0].copy();x['prediction']=statistics.mean(float(z['prediction']) for z in v);x['absolute_error']=abs(float(x['actual'])-x['prediction']);meanrows.append(x)
   candidates.append({'candidate_id':f'P10-{target}-{model}-{fs}','target':target,'model':model,'feature_set':fs,'mae':mae(meanrows),'feature_count':complexity,'complexity':complexity,'runtime':0.0,'rows':meanrows,'framework':'pytorch' if model=='mlp' else 'sklearn','implementation_id':'PYTORCH_MLP_V1' if model=='mlp' else model.upper()})
  ref=choose_reference(candidates); challenger=[x for x in candidates if x is not ref]
  b=[r for r in base if r['target']==target and r['horizon']==24 and r['baseline_id']==baselines[target]];bm={r['target_timestamp']:r for r in b}; pairs=[(r,bm[r['target_timestamp']]) for r in ref['rows'] if r['target_timestamp'] in bm];d=[float(r['absolute_error'])-float(q['absolute_error']) for r,q in pairs];n=len(d);v=statistics.pvariance(d);stat=statistics.mean(d)/math.sqrt(v/n) if v else 0.;p=math.erfc(abs(stat)/math.sqrt(2)); comparisons.append({'target':target,'candidate':ref['candidate_id'],'comparator':baselines[target],'comparison_type':'PRIMARY DEVELOPMENT ONLY','n_paired_observations':n,'MAE_candidate':mae([x[0] for x in pairs]),'MAE_comparator':mae([x[1] for x in pairs]),'relative_improvement_pct':100*(mae([x[1] for x in pairs])-mae([x[0] for x in pairs]))/mae([x[1] for x in pairs]),'test_statistic':stat,'raw_p_value':p}); selected.append({k:v for k,v in ref.items() if k!='rows'});registry[target]={'reference_model':{k:v for k,v in ref.items() if k!='rows'},'challengers':[{k:v for k,v in x.items() if k!='rows'} for x in challenger],'baseline_comparator':baselines[target]}
 adj=holm([x['raw_p_value'] for x in comparisons]);[x.update(adjusted_p_value=a,interpretation='DEVELOPMENT ONLY') for x,a in zip(comparisons,adj)]
 def wr(path,rows):
  with Path(path).open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 wr(out/'forecasting_candidate_synthesis.csv',selected);wr(out/'development_paired_comparisons.csv',comparisons)
 regpath=ROOT/'artifacts/model_registry';regpath.mkdir(parents=True,exist_ok=True);(regpath/'forecasting_reference_registry.yaml').write_text(json.dumps(registry,indent=2)+'\n')
 freeze={'phase':'11','references':selected,'challengers':registry,'selection_protocol_checksum':sha(ROOT/'artifacts/experimental_design/phase_11_finalist_selection_protocol_freeze.yaml'),'final_test_access':{'training':False,'hpo':False,'selection':False,'performance':False}}
 fp=ROOT/'artifacts/experimental_design/phase_11_forecasting_finalist_freeze.yaml';fp.write_text(json.dumps(freeze,indent=2)+'\n'); plan={'status':'FROZEN_NOT_EXECUTED','horizon':24,'primary_metric':'MAE','test':'Diebold-Mariano absolute error; Holm-Bonferroni','hypotheses':['FT-H1-LOAD','FT-H1-WIND','FT-H1-PV'],'matrix':registry,'final_test_authorization_required':True};pp=ROOT/'artifacts/experimental_design/final_test_comparison_plan.yaml';pp.write_text(json.dumps(plan,indent=2)+'\n');print(json.dumps({'references':selected,'comparisons':comparisons},indent=2))
if __name__=='__main__':main()
