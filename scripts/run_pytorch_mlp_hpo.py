from __future__ import annotations
import json,sys,time,random,csv
from pathlib import Path
import numpy as np,optuna,torch,pyarrow.parquet as pq
from sklearn.preprocessing import StandardScaler
from torch import nn
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from smartgrid_mlops.models.neural.base import MLP
from smartgrid_mlops.experimental_design.rolling_origin import fold_boundaries
from smartgrid_mlops.experimental_design.metrics import mae
import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stderr,
)
LOGGER = logging.getLogger(__name__)
F=['hour_sin','hour_cos','dow_sin','dow_cos','doy_sin','doy_cos','lag_1','lag_24','lag_168','rolling_mean_24','rolling_mean_168','ramp_1h'];COL={'load':('load_hourly.parquet','actual_system_load'),'wind':('wind_hourly.parquet','actual_wind'),'pv':('pv_hourly.parquet','actual_pv')}
def run(target):
 r=pq.read_table(ROOT/'data/processed'/COL[target][0]).to_pylist();a={x['timestamp']:x[COL[target][1]] for x in r};rows=pq.read_table(ROOT/f'data/processed/features/{target}/h24/combined_v1.parquet',columns=['target_timestamp',*F]).to_pylist();out=ROOT/'artifacts/experiments/hpo/phase_09/studies';out.mkdir(parents=True,exist_ok=True);study=optuna.create_study(study_name=f'phase09-{target}-pytorch-mlp-v1-recovery',storage=f"sqlite:///{(out/f'{target}_pytorch_mlp_v1_recovery.db').as_posix()}",load_if_exists=True,direction='minimize',sampler=optuna.samplers.TPESampler(seed=42))
 def obj(tr):
  vals=[];st=time.perf_counter();
  for fold in fold_boundaries()[:4]:
   train=[x for x in rows if fold['training_start']<=x['target_timestamp']<fold['training_end_exclusive']];val=[x for x in rows if fold['validation_start']<=x['target_timestamp']<fold['validation_end_exclusive']];xs=StandardScaler();ys=StandardScaler();X=xs.fit_transform([[x[k] for k in F] for x in train]);V=xs.transform([[x[k] for k in F] for x in val]);Y=ys.fit_transform(np.array([a[x['target_timestamp']] for x in train]).reshape(-1,1)).ravel();n=int(.9*len(train));random.seed(42);np.random.seed(42);torch.manual_seed(42);m=MLP(len(F),(tr.suggest_int('hidden_width',32,128),32),tr.suggest_float('dropout',0,.4));opt=torch.optim.Adam(m.parameters(),lr=tr.suggest_float('learning_rate',1e-4,5e-3,log=True),weight_decay=tr.suggest_float('weight_decay',1e-8,1e-2,log=True));loss=nn.MSELoss();best=1e99;state=None;pat=0
   for e in range(12):
    opt.zero_grad();o=m(torch.tensor(X[:n],dtype=torch.float32));l=loss(o,torch.tensor(Y[:n],dtype=torch.float32));l.backward();opt.step()
    with torch.no_grad():iv=float(loss(m(torch.tensor(X[n:],dtype=torch.float32)),torch.tensor(Y[n:],dtype=torch.float32)))
    if iv<best:best=iv;state={k:v.clone() for k,v in m.state_dict().items()};pat=0
    else:pat+=1
    if pat>=4:break
   m.load_state_dict(state);p=ys.inverse_transform(m(torch.tensor(V,dtype=torch.float32)).detach().numpy().reshape(-1,1)).ravel();vals.append(mae([a[x['target_timestamp']] for x in val],p))
  vals=[float(x) for x in vals];tr.set_user_attr('framework','pytorch');tr.set_user_attr('implementation_id',MLP.implementation_id);tr.set_user_attr('fold_mae',vals);tr.set_user_attr('runtime',float(time.perf_counter()-st));return float(sum(vals)/4)
 _trials = int(os.environ.get("SMARTGRID_MLOPS_HPO_TRIALS", "5"))
 study.optimize(obj,n_trials=max(0,_trials-len(study.trials)));return study
if __name__=='__main__':
 studies=[run(t) for t in COL];LOGGER.info([(s.study_name,s.best_value,s.best_params) for s in studies])
