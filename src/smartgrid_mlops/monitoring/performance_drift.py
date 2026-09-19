import numpy as np
from .feature_drift import normalized_wasserstein
def rolling_mae(y,pred,window=168):
    y,pred=np.asarray(y,float),np.asarray(pred,float)
    if len(y)<window:return float("nan")
    return float(np.mean(np.abs(y[-window:]-pred[-window:])))
def performance_signals(ref_y,ref_pred,cur_y,cur_pred):
    re=np.abs(np.asarray(ref_y)-np.asarray(ref_pred));ce=np.abs(np.asarray(cur_y)-np.asarray(cur_pred));return {"rolling_mae":rolling_mae(cur_y,cur_pred),"calibration_mae":float(np.mean(re)),"mae_degradation":float(np.mean(ce)-np.mean(re)),"error_wasserstein":normalized_wasserstein(re,ce)}
