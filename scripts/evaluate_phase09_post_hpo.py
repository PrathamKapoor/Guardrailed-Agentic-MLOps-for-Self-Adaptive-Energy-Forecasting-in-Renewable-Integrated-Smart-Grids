from pathlib import Path
import json,csv,sys,hashlib
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from run_neural_experiments import rows,actual,fit_predict,F
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
def main():
 out=ROOT/'artifacts/experiments/hpo/phase_09/post_hpo_validation';out.mkdir(parents=True,exist_ok=True);run=[];pred=[];freeze=(ROOT/'artifacts/experimental_design/phase_09_selected_config_freeze.yaml');fh=hashlib.sha256(freeze.read_bytes()).hexdigest()
 for target in ('load','wind','pv'):
  cfg=json.loads((ROOT/f'artifacts/experiments/hpo/phase_09/best_configs/{target}_pytorch_mlp.yaml').read_text());base=json.loads((ROOT/'config/models/neural_untuned_v1.yaml').read_text());base.update({'learning_rate':cfg['hyperparameters']['learning_rate'],'batch_size':64,'hidden_width':cfg['hyperparameters']['hidden_width'],'dropout':cfg['hyperparameters']['dropout']});base['maximum_epochs']=12;base['early_stopping_patience']=4
  fr=rows(target,24);am=actual(target)
  for fold in fold_boundaries()[4:]:
   tr=[r for r in fr if fold['training_start']<=r['target_timestamp']<fold['training_end_exclusive']];va=[r for r in fr if fold['validation_start']<=r['target_timestamp']<fold['validation_end_exclusive']]
   for r in tr+va:r['actual']=am[r['target_timestamp']]
   for seed in (42,123,2020,2025,31415):
    p,ts,ps,b,e,count,h=fit_predict('mlp',tr,va,seed,base);a=[r['actual'] for r in va];m={'MAE':mae(a,p),'RMSE':rmse(a,p),'sMAPE':smape(a,p),'nMAE':nmae(a,p),'nRMSE':nrmse(a,p)};run.append({'target':target,'fold':fold['fold_id'],'seed':seed,'framework':'pytorch','implementation_id':'PYTORCH_MLP_V1','selected_trial_id':cfg['selected_trial_id'],'best_epoch':b,'stopped_epoch':e,'training_seconds':ts,'prediction_seconds':ps,'parameter_count':count,'negative_prediction_count':sum(x<0 for x in p),**m})
    for r,x in zip(va,p):pred.append({'target':target,'fold':fold['fold_id'],'seed':seed,'framework':'pytorch','implementation_id':'PYTORCH_MLP_V1','forecast_origin':r['forecast_origin'],'target_timestamp':r['target_timestamp'],'actual':r['actual'],'prediction':float(x),'error':float(r['actual']-x),'absolute_error':abs(float(r['actual']-x)),'squared_error':float((r['actual']-x)**2)})
 def wr(path,data):
  with path.open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
 wr(out/'metrics.csv',run);wr(out/'predictions.csv',pred);LOGGER.info(len(run))
if __name__=='__main__':main()
