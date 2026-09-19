#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,json,sys,time
from pathlib import Path
import optuna,pyarrow.parquet as pq
from sklearn.ensemble import RandomForestRegressor,HistGradientBoostingRegressor
from sklearn.neural_network import MLPRegressor
from smartgrid_mlops.experimental_design.metrics import mae
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from smartgrid_mlops.experimental_design.rolling_origin import fold_boundaries
import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stderr,
)
LOGGER = logging.getLogger(__name__)
F=['hour_sin','hour_cos','dow_sin','dow_cos','doy_sin','doy_cos','lag_1','lag_24','lag_168','rolling_mean_24','rolling_mean_168','ramp_1h'];COL={'load':('load_hourly.parquet','actual_system_load'),'wind':('wind_hourly.parquet','actual_wind'),'pv':('pv_hourly.parquet','actual_pv')}
def data(t):
 r=pq.read_table(ROOT/'data/processed'/COL[t][0],columns=['timestamp',COL[t][1]]).to_pylist();a={x['timestamp']:x[COL[t][1]] for x in r};q=pq.read_table(ROOT/f'data/processed/features/{t}/h24/combined_v1.parquet',columns=['forecast_origin','target_timestamp',*F]).to_pylist();return q,a
def model(name,tr):
 if name=='random_forest':return RandomForestRegressor(n_estimators=tr.suggest_int('n_estimators',100,300),max_depth=tr.suggest_categorical('max_depth',[None,8,16,24]),min_samples_split=tr.suggest_int('min_samples_split',2,12),min_samples_leaf=tr.suggest_int('min_samples_leaf',1,6),max_features=tr.suggest_categorical('max_features',['sqrt','log2',1.0]),bootstrap=tr.suggest_categorical('bootstrap',[True,False]),random_state=42,n_jobs=-1)
 if name=='hist_gradient_boosting':return HistGradientBoostingRegressor(learning_rate=tr.suggest_float('learning_rate',.01,.2,log=True),max_iter=tr.suggest_int('max_iter',100,300),max_leaf_nodes=tr.suggest_int('max_leaf_nodes',15,63),min_samples_leaf=tr.suggest_int('min_samples_leaf',10,40),l2_regularization=tr.suggest_float('l2_regularization',1e-8,10,log=True),random_state=42)
 return MLPRegressor(hidden_layer_sizes=(tr.suggest_int('hidden_width',32,128),),activation=tr.suggest_categorical('activation',['relu','identity']),alpha=tr.suggest_float('weight_decay',1e-8,1e-2,log=True),learning_rate_init=tr.suggest_float('learning_rate',1e-4,5e-3,log=True),batch_size=tr.suggest_categorical('batch_size',[32,64,128]),max_iter=50,early_stopping=True,random_state=42)
def main():
 p=argparse.ArgumentParser();p.add_argument('--all',action='store_true');p.add_argument('--target',action='append');p.add_argument('--model',action='append');p.add_argument('--smoke',action='store_true');a=p.parse_args();cfg=json.loads((ROOT/'config/hpo/phase_09.yaml').read_text());targets=a.target or ['load','wind','pv'];pairs={'load':['random_forest','mlp'],'wind':['hist_gradient_boosting','mlp'],'pv':['random_forest','mlp']};hist=[];best=[]
 for t in targets:
  rows,actual=data(t)
  for name in (a.model or pairs[t]):
   storage=f"sqlite:///{(ROOT/'artifacts/experiments/hpo/phase_09/studies'/f'{t}_{name}.db').as_posix()}";(ROOT/'artifacts/experiments/hpo/phase_09/studies').mkdir(parents=True,exist_ok=True)
   study=optuna.create_study(study_name=f'phase09_{t}_{name}',storage=storage,load_if_exists=True,direction='minimize',sampler=optuna.samplers.TPESampler(seed=42))
   def obj(tr):
    vals=[];start=time.perf_counter()
    for f in fold_boundaries()[:4]:
     train=[r for r in rows if f['training_start']<=r['target_timestamp']<f['training_end_exclusive']];val=[r for r in rows if f['validation_start']<=r['target_timestamp']<f['validation_end_exclusive']];m=model(name,tr);m.fit([[r[x] for x in F] for r in train],[actual[r['target_timestamp']] for r in train]);pr=m.predict([[r[x] for x in F] for r in val]);vals.append(mae([actual[r['target_timestamp']] for r in val],pr))
    tr.set_user_attr('runtime_seconds',time.perf_counter()-start);tr.set_user_attr('fold_mae',vals);return sum(vals)/len(vals)
   n=1 if a.smoke else cfg['trials_per_study'];study.optimize(obj,n_trials=n-len(study.trials),catch=(Exception,))
   for tr in study.trials:hist.append({'study_id':study.study_name,'trial_id':tr.number,'target':t,'model':name,'params':json.dumps(tr.params,sort_keys=True),'mean_MAE':tr.value,'status':str(tr.state),'runtime_seconds':tr.user_attrs.get('runtime_seconds'),'fold_MAE':json.dumps(tr.user_attrs.get('fold_mae',[]))})
   b=study.best_trial;best.append({'target':t,'model':name,'trial_id':b.number,'search_MAE':b.value,'params':json.dumps(b.params,sort_keys=True)})
 out=ROOT/'artifacts/experiments/hpo/phase_09';out.mkdir(parents=True,exist_ok=True)
 def wr(path,d):
  path.parent.mkdir(parents=True,exist_ok=True)
  with path.open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(d[0]));w.writeheader();w.writerows(d)
 wr(ROOT/'artifacts/research_tables/hpo_trial_history.csv',hist);wr(out/'best_configs/best_configs.csv',best);print(json.dumps({'completed':len(hist),'best':best},indent=2))
if __name__=='__main__':main()
