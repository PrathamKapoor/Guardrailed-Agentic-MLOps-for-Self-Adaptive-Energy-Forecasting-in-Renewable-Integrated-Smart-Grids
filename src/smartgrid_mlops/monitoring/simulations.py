import numpy as np
def development_stream(target,n=1008,seed=42):
    rng=np.random.default_rng(seed+sum(map(ord,target)));scale={"load":100.,"wind":60.,"pv":15.}[target];x=rng.normal(0,scale,(n,3));y=rng.normal(0,scale,n);pred=y+rng.normal(0,scale*.2,n);return x,y,pred
def perturb(x,y,pred,family,severity,seed=42):
    x,y,pred=np.array(x,copy=True),np.array(y,copy=True),np.array(pred,copy=True);onset=len(x)//2;mag={"LOW":.5,"MEDIUM":1.,"HIGH":2.}[severity]
    if family in {"D01","D02","D03","D08"}:x[onset:]+=mag*np.std(x[:onset],axis=0)
    if family in {"D03","D07","D08"}:x[onset:]*=(1+.5*mag)
    if family in {"D04","D09"}:x[onset:,0]=np.nan
    if family in {"D05","D08"}:pred[onset:]+=mag*np.std(pred[:onset])
    if family in {"D06","D07","D08"}:pred[onset:]+=mag*np.std(y[:onset])
    return x,y,pred,onset
