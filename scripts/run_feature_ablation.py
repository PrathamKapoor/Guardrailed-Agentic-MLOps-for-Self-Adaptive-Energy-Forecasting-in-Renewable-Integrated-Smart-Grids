#!/usr/bin/env python3
"""Phase 10 H24 ablation runner; deliberately has no final-test option."""
from __future__ import annotations
import argparse,csv,hashlib,json,random,time
from datetime import datetime
from pathlib import Path
import sys
import numpy as np, pyarrow as pa, pyarrow.parquet as pq, torch
from sklearn.ensemble import RandomForestRegressor,HistGradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from torch import nn
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from smartgrid_mlops.models.neural.base import MLP
from smartgrid_mlops.experimental_design.rolling_origin import fold_boundaries
from smartgrid_mlops.experimental_design.metrics import mae,rmse,smape,nmae,nrmse
from smartgrid_mlops.ablation.selection import select_feature_set
from smartgrid_mlops.ablation.common_samples import common_timestamp_intersection
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stderr,
)
LOGGER = logging.getLogger(__name__)
FINAL=datetime(2020,11,1); SEEDS=(42,123,2020,2025,31415); COL={'load':('load_hourly.parquet','actual_system_load'),'wind':('wind_hourly.parquet','actual_wind'),'pv':('pv_hourly.parquet','actual_pv')}
def load_config():return json.loads((ROOT/'config/ablation/phase_10.yaml').read_text())
def load_rows(target):
 return pq.read_table(ROOT/f'data/processed/features/{target}/h24/combined_v1.parquet',filters=[('target_timestamp','<',FINAL)]).to_pylist()
def actuals(target):
 f,c=COL[target]; return {r['timestamp']:float(r[c]) for r in pq.read_table(ROOT/'data/processed'/f,columns=['timestamp',c],filters=[('timestamp','<',FINAL)]).to_pylist()}
def metrics(a,p):return {'MAE':mae(a,p),'RMSE':rmse(a,p),'sMAPE':smape(a,p),'nMAE':nmae(a,p),'nRMSE':nrmse(a,p)}
def fit_classical(kind,params,features,train,val):
 m=RandomForestRegressor(**params) if kind=='random_forest' else HistGradientBoostingRegressor(**params);start=time.perf_counter();m.fit([[r[x] for x in features] for r in train],[r['actual'] for r in train]);tr=time.perf_counter()-start;start=time.perf_counter();p=m.predict([[r[x] for x in features] for r in val]);return p,tr,time.perf_counter()-start
def fit_mlp(params,features,train,val,seed):
 random.seed(seed);np.random.seed(seed);torch.manual_seed(seed);torch.use_deterministic_algorithms(True,warn_only=True)
 xs,ys=StandardScaler(),StandardScaler(); X=xs.fit_transform(np.array([[r[x] for x in features] for r in train],dtype=np.float32));V=xs.transform(np.array([[r[x] for x in features] for r in val],dtype=np.float32));Y=ys.fit_transform(np.array([r['actual'] for r in train],dtype=np.float32).reshape(-1,1)).ravel();n=max(1,int(.9*len(train)));m=MLP(len(features),(int(params['hidden_width']),32),float(params['dropout']));opt=torch.optim.Adam(m.parameters(),lr=float(params['learning_rate']),weight_decay=float(params['weight_decay']));loss=nn.MSELoss();best=float('inf');state=None;pat=0;start=time.perf_counter()
 for epoch in range(12):
  m.train();opt.zero_grad();out=m(torch.tensor(X[:n]));l=loss(out,torch.tensor(Y[:n]));l.backward();opt.step();m.eval()
  with torch.no_grad():iv=float(loss(m(torch.tensor(X[n:])),torch.tensor(Y[n:])))
  if iv<best:best=iv;state={k:v.clone() for k,v in m.state_dict().items()};pat=0
  else:pat+=1
  if pat>=4:break
 m.load_state_dict(state)
 with torch.no_grad():p=m(torch.tensor(V)).numpy().ravel()
 return ys.inverse_transform(p.reshape(-1,1)).ravel(),time.perf_counter()-start,epoch+1
def write_csv(path,rows):
 path.parent.mkdir(parents=True,exist_ok=True)
 with path.open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--all',action='store_true');ap.add_argument('--smoke',action='store_true');ap.add_argument('--confirmation',action='store_true');ap.add_argument('--target',action='append',choices=COL);ap.add_argument('--model',action='append',choices=('classical','mlp'));a=ap.parse_args()
 if not(a.all or a.smoke or a.confirmation or a.target or a.model):ap.error('use --all, --smoke, --confirmation, or scoped target/model')
 cfg=load_config(); protocol=json.loads((ROOT/'artifacts/experimental_design/phase_10_ablation_protocol_freeze.yaml').read_text()); selected={(x['target'],x['model']):x['selected_feature_set'] for x in json.loads((ROOT/'artifacts/experimental_design/phase_10_selected_feature_freeze.yaml').read_text()).get('selections',[])}; targets=a.target or list(COL);models=a.model or ['classical','mlp']; folds=fold_boundaries()[4:] if a.confirmation else (fold_boundaries()[:1] if a.smoke else fold_boundaries()[:4]);out=ROOT/'artifacts/experiments/ablation/phase_10'/('smoke' if a.smoke else ('confirmation' if a.confirmation else 'official')); allpred=[];run=[];common_manifest=[]
 for target in targets:
  rows=load_rows(target);amap=actuals(target); feature_ids=([selected[(target,protocol['classical_models'][target]['model'])]] if a.confirmation else (['A_calendar_only'] if a.smoke else cfg['classical_feature_sets'])) if 'classical' in models else []; mlp_ids=([selected[(target,'mlp')]] if a.confirmation else (['A_calendar_only'] if a.smoke else cfg['mlp_anchor_feature_sets'])) if 'mlp' in models else []
  for fold in folds:
   base=[r for r in rows if fold['training_start']<=r['target_timestamp']<fold['training_end_exclusive'] or fold['validation_start']<=r['target_timestamp']<fold['validation_end_exclusive']]; feature_rows={fid:base for fid in set(feature_ids+mlp_ids)};common=common_timestamp_intersection(feature_rows);common_manifest.append({'target':target,'fold':fold['fold_id'],'original_sample_count_by_feature_set':json.dumps({x:len(base) for x in feature_rows}),'common_comparison_sample_count':len(common),'timestamps_removed_by_intersection':0,'first_comparison_timestamp':str(min(x[1] for x in common)),'last_comparison_timestamp':str(max(x[1] for x in common))})
   tr=[dict(r,actual=amap[r['target_timestamp']]) for r in base if r['target_timestamp']<fold['training_end_exclusive'] and (r['forecast_origin'],r['target_timestamp']) in common];va=[dict(r,actual=amap[r['target_timestamp']]) for r in base if r['target_timestamp']>=fold['validation_start'] and (r['forecast_origin'],r['target_timestamp']) in common]
   for family,fids in [('classical',feature_ids),('mlp',mlp_ids)]:
    if family not in models:continue
    for fid in fids:
     feats=cfg['feature_sets'][fid]; seeds=(42,) if family=='classical' else (SEEDS[:1] if a.smoke else SEEDS)
     for seed in seeds:
      if family=='classical':pred,trsec,prsec=fit_classical(protocol['classical_models'][target]['model'],protocol['classical_models'][target]['hyperparameters'],feats,tr,va);epochs='N/A';impl=protocol['classical_models'][target]['implementation_id'];model=protocol['classical_models'][target]['model']
      else: params=json.loads((ROOT/f'artifacts/experiments/hpo/phase_09/best_configs/{target}_pytorch_mlp.yaml').read_text())['hyperparameters'];pred,trsec,epochs=fit_mlp(params,feats,tr,va,seed);prsec=0.;impl='PYTORCH_MLP_V1';model='mlp'
      rid=f'P10-{target}-{model}-{fid}-{fold["fold_id"]}-S{seed}';m=metrics([r['actual'] for r in va],pred);run.append({'run_id':rid,'evidence_status':'NON_EVIDENCE_SMOKE' if a.smoke else 'VALID','target':target,'model':model,'framework':'pytorch' if family=='mlp' else 'sklearn','implementation_id':impl,'feature_set':fid,'feature_count':len(feats),'fold':fold['fold_id'],'seed':seed,'training_seconds':trsec,'prediction_seconds':prsec,'epochs':epochs,**m})
      for r,p in zip(va,pred):allpred.append({'run_id':rid,'evidence_status':'NON_EVIDENCE_SMOKE' if a.smoke else 'VALID','target':target,'model':model,'feature_set':fid,'fold':fold['fold_id'],'seed':seed,'forecast_origin':r['forecast_origin'],'target_timestamp':r['target_timestamp'],'actual':r['actual'],'prediction':float(p),'error':float(r['actual']-p),'absolute_error':abs(float(r['actual']-p)),'squared_error':float((r['actual']-p)**2)})
 write_csv(out/'metrics/run_metrics.csv',run);write_csv(out/'manifests/common_sample_manifest.csv',common_manifest);(out/'predictions').mkdir(parents=True,exist_ok=True);pq.write_table(pa.Table.from_pylist(allpred),out/'predictions/predictions.parquet');print(json.dumps({'evidence_status':'NON_EVIDENCE_SMOKE' if a.smoke else 'VALID','runs':len(run),'prediction_rows':len(allpred),'final_test_access':False},indent=2))
if __name__=='__main__':main()
