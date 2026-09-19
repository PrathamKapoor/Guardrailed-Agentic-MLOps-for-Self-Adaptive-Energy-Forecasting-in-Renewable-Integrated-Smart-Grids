#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,json,random,sys,time,hashlib,platform
from collections import defaultdict
from datetime import datetime
from pathlib import Path
import numpy as np, pyarrow as pa, pyarrow.parquet as pq, torch
from sklearn.preprocessing import StandardScaler
from torch import nn
from torch.utils.data import DataLoader,TensorDataset
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from smartgrid_mlops.models.neural.base import MLP,Recurrent,parameter_count
from smartgrid_mlops.models.neural.sequences import build_sequences
from smartgrid_mlops.models.validation import reject_final_test
from smartgrid_mlops.experimental_design.rolling_origin import fold_boundaries
from smartgrid_mlops.experimental_design.metrics import mae,rmse,smape,nmae,nrmse
import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stderr,
)
LOGGER = logging.getLogger(__name__)
F=('hour_sin','hour_cos','dow_sin','dow_cos','doy_sin','doy_cos','lag_1','lag_24','lag_168','rolling_mean_24','rolling_mean_168','ramp_1h'); C=F[:6]; SEEDS=(42,123,2020,2025,31415); MODELS=('mlp','lstm','gru'); COL={'load':('load_hourly.parquet','actual_system_load'),'wind':('wind_hourly.parquet','actual_wind'),'pv':('pv_hourly.parquet','actual_pv')}
def config():return json.loads((ROOT/'config/models/neural_untuned_v1.yaml').read_text())
def setseed(s):random.seed(s);np.random.seed(s);torch.manual_seed(s);torch.use_deterministic_algorithms(True,warn_only=True)
def metrics(a,p):return {'MAE':mae(a,p),'RMSE':rmse(a,p),'sMAPE':smape(a,p),'nMAE':nmae(a,p),'nRMSE':nrmse(a,p)}
def rows(t,h):return pq.read_table(ROOT/f'data/processed/features/{t}/h{h}/combined_v1.parquet',columns=['forecast_origin','target_timestamp',*F]).to_pylist()
def actual(t):
 f,c=COL[t];return {r['timestamp']:float(r[c]) for r in pq.read_table(ROOT/'data/processed'/f,columns=['timestamp',c]).to_pylist()}
def fit_predict(modelkind,train,val,seed,cfg):
 setseed(seed); device=torch.device('cpu'); xscale=StandardScaler();yscale=StandardScaler();
 if modelkind=='mlp':
  X=np.array([[r[k] for k in F] for r in train],dtype=np.float32); V=np.array([[r[k] for k in F] for r in val],dtype=np.float32); X=xscale.fit_transform(X); V=xscale.transform(V)
 else:
  X=np.array([r['sequence'] for r in train],dtype=np.float32);V=np.array([r['sequence'] for r in val],dtype=np.float32)
  X[:,:,0]=xscale.fit_transform(X[:,:,0].reshape(-1,1)).reshape(X.shape[:2]);V[:,:,0]=xscale.transform(V[:,:,0].reshape(-1,1)).reshape(V.shape[:2])
 Y=np.array([r['actual'] for r in train],dtype=np.float32).reshape(-1,1);Y=yscale.fit_transform(Y).ravel();
 n=max(1,int(len(train)*.9)); inner=TensorDataset(torch.tensor(X[:n]),torch.tensor(Y[:n])); inner_val=(torch.tensor(X[n:]),torch.tensor(Y[n:]))
 if modelkind=='mlp':model=MLP(len(F),(cfg.get('hidden_width',64),32),cfg.get('dropout',.1)).to(device)
 else:model=Recurrent(modelkind,7,32).to(device)
 opt=torch.optim.Adam(model.parameters(),lr=cfg['learning_rate']);lossfn=nn.MSELoss();best=float('inf');state=None;patience=0;hist=[];start=time.perf_counter()
 for epoch in range(cfg['maximum_epochs']):
  model.train()
  for xb,yb in DataLoader(inner,batch_size=cfg['batch_size'],shuffle=True,generator=torch.Generator().manual_seed(seed+epoch)):
   opt.zero_grad();out=model(xb) if modelkind=='mlp' else model(xb,torch.tensor(np.array([r['future_calendar'] for r in train[:n]],dtype=np.float32))[0:len(xb)]) if False else None
   if modelkind!='mlp':
    # recurrent loader needs calendar paired; index-free full-batch batches are reconstructed below
    break
   loss=lossfn(out,yb);loss.backward();opt.step()
  if modelkind!='mlp':
   model.train(); opt.zero_grad(); xx=torch.tensor(X[:n]);fc=torch.tensor(np.array([r['future_calendar'] for r in train[:n]],dtype=np.float32));out=model(xx,fc);loss=lossfn(out,torch.tensor(Y[:n]));loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),cfg['gradient_clip_norm']);opt.step()
  model.eval()
  with torch.no_grad():
   if modelkind=='mlp':iv=model(inner_val[0]);
   else:iv=model(inner_val[0],torch.tensor(np.array([r['future_calendar'] for r in train[n:]],dtype=np.float32)))
   il=float(lossfn(iv,inner_val[1]));hist.append((epoch+1,float(loss),il))
  if not np.isfinite(il):raise RuntimeError('non-finite inner validation loss')
  if il<best:best=il;state={k:v.clone() for k,v in model.state_dict().items()};best_epoch=epoch+1;patience=0
  else:patience+=1
  if patience>=cfg['early_stopping_patience']:break
 model.load_state_dict(state);trainsec=time.perf_counter()-start;start=time.perf_counter();model.eval()
 with torch.no_grad(): pred=model(torch.tensor(V)) if modelkind=='mlp' else model(torch.tensor(V),torch.tensor(np.array([r['future_calendar'] for r in val],dtype=np.float32)))
 pred=yscale.inverse_transform(pred.numpy().reshape(-1,1)).ravel();return pred,trainsec,time.perf_counter()-start,best_epoch,epoch+1,parameter_count(model),hist
def main():
 p=argparse.ArgumentParser();p.add_argument('--all',action='store_true');p.add_argument('--smoke',action='store_true');p.add_argument('--target',action='append',choices=COL);p.add_argument('--horizon',action='append',type=int,choices=(1,24));p.add_argument('--model',action='append',choices=MODELS);a=p.parse_args();cfg=config();out=ROOT/'artifacts/experiments/neural/phase_08';preds=[];run=[];history=[]
 targets=a.target or tuple(COL); horizons=a.horizon or (1,24); models=a.model or MODELS; folds=fold_boundaries()[:1] if a.smoke else fold_boundaries()
 for t in targets:
  raw=rows(t,1); amap=actual(t)
  for h in horizons:
   fr=rows(t,h);seq=build_sequences(fr,amap,cfg['sequence_length']);seqmap={r['target_timestamp']:r for r in seq}
   for fold in folds:
    tabtrain=[r for r in fr if fold['training_start']<=r['target_timestamp']<fold['training_end_exclusive']];tabval=[r for r in fr if fold['validation_start']<=r['target_timestamp']<fold['validation_end_exclusive']]
    for m in models:
     train=tabtrain if m=='mlp' else [seqmap[r['target_timestamp']] for r in tabtrain if r['target_timestamp'] in seqmap];val=tabval if m=='mlp' else [seqmap[r['target_timestamp']] for r in tabval if r['target_timestamp'] in seqmap]
     for r in train+val:r['actual']=amap[r['target_timestamp']]
     run_seeds=SEEDS[:1] if (a.smoke or h==1) else SEEDS
     for s in run_seeds:
      exp=f'{t.upper()}-H{h}-{m.upper()}-NNV1-S{s}-{fold["fold_id"]}'
      try: pr,tr,pt,best,stopped,count,hist=fit_predict(m,train,val,s,cfg);status='SUCCESS';reason=''
      except Exception as e:pr=[];tr=pt=0;best=stopped=count=0;hist=[];status='FAILED';reason=str(e)
      run.append({'experiment_id':exp,'target':t,'horizon':h,'model':m,'track':'tabular' if m=='mlp' else 'sequence','fold':fold['fold_id'],'seed':s,'training_seconds':tr,'prediction_seconds':pt,'best_epoch':best,'stopped_epoch':stopped,'parameter_count':count,'training_status':status,'failure_reason':reason,'samples':len(val)})
      for ep,tl,il in hist:history.append({'experiment_id':exp,'epoch':ep,'training_loss':tl,'inner_validation_loss':il,'best_epoch':best,'stopped_epoch':stopped})
      if status=='SUCCESS':
       for r,q in zip(val,pr):preds.append({'experiment_id':exp,'track':'tabular' if m=='mlp' else 'sequence','target':t,'horizon':h,'model':m,'seed':s,'fold':fold['fold_id'],'forecast_origin':r['forecast_origin'],'target_timestamp':r['target_timestamp'],'actual':r['actual'],'prediction':float(q),'error':float(r['actual']-q),'absolute_error':abs(float(r['actual']-q)),'squared_error':float((r['actual']-q)**2),'sequence_length':None if m=='mlp' else cfg['sequence_length']})
 out.mkdir(parents=True,exist_ok=True);(out/'predictions').mkdir(exist_ok=True);pq.write_table(pa.Table.from_pylist(preds),out/'predictions/neural_predictions.parquet')
 def wr(path,data):
  if not data:return
  path.parent.mkdir(parents=True,exist_ok=True)
  with path.open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
 wr(out/'metrics/run_metadata.csv',run);wr(out/'training_history/history.csv',history)
 # per seed aggregate across folds (relevant sample rows only)
 agg=[]
 for key in sorted(set((x['target'],x['horizon'],x['model'],x['seed']) for x in preds)):
  z=[x for x in preds if (x['target'],x['horizon'],x['model'],x['seed'])==key];agg.append({'target':key[0],'horizon':key[1],'model':key[2],'seed':key[3],**metrics([x['actual'] for x in z],[x['prediction'] for x in z])})
 wr(ROOT/'artifacts/research_tables/neural_seed_stability.csv',agg)
 # seed mean predictions then outer validation overall
 g=defaultdict(list)
 for x in preds:g[(x['target'],x['horizon'],x['model'],x['target_timestamp'])].append(x)
 summary=[]
 for key in sorted(set((x['target'],x['horizon'],x['model']) for x in preds)):
  z=[]; for_key=[v for k,v in g.items() if k[:3]==key]
  for v in for_key:z.append((v[0]['actual'],sum(x['prediction'] for x in v)/len(v)))
  mtr=metrics([x[0] for x in z],[x[1] for x in z]);std=float(np.std([x['MAE'] for x in agg if x['target']==key[0] and x['horizon']==key[1] and x['model']==key[2]]));summary.append({'target':key[0],'horizon':key[1],'track':'tabular' if key[2]=='mlp' else 'sequence','model':key[2],'sequence_length':'N/A' if key[2]=='mlp' else cfg['sequence_length'],**mtr,'std_across_seeds_MAE':std,'samples':len(z)})
 wr(out/'metrics/aggregate_metrics.csv',summary);tables=ROOT/'artifacts/research_tables';wr(tables/'neural_h24_validation_results.csv',[x for x in summary if x['horizon']==24]);wr(tables/'neural_h1_validation_results.csv',[x for x in summary if x['horizon']==1]);
 print(json.dumps({'successful_runs':sum(x['training_status']=='SUCCESS' for x in run),'failed_runs':sum(x['training_status']=='FAILED' for x in run),'prediction_rows':len(preds)},indent=2))
if __name__=='__main__':main()
