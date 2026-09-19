import numpy as np
def _bins(ref,count=10):
    r=np.asarray(ref,float); e=np.unique(np.quantile(r[np.isfinite(r)],np.linspace(0,1,count+1)))
    if len(e)<2:e=np.array([float(np.nanmin(r))-.5,float(np.nanmax(r))+.5])
    e[0]=-np.inf;e[-1]=np.inf;return e
def psi(reference,current,bins=10,epsilon=1e-6):
    r,c=np.asarray(reference,float),np.asarray(current,float);e=_bins(r,bins);rp=np.histogram(r,e)[0].astype(float);cp=np.histogram(c,e)[0].astype(float);rp=rp/max(rp.sum(),1)+epsilon;cp=cp/max(cp.sum(),1)+epsilon;return float(np.sum((cp-rp)*np.log(cp/rp)))
def normalized_wasserstein(reference,current,scale=None):
    r=np.sort(np.asarray(reference,float));c=np.sort(np.asarray(current,float))
    if not r.size or not c.size:return float("nan")
    q=np.linspace(0,1,max(len(r),len(c)));rv=np.quantile(r,q);cv=np.quantile(c,q)
    if scale is None:scale=float(np.subtract(*np.percentile(r,[75,25])))
    if not np.isfinite(scale) or scale==0:scale=1.
    return float(np.mean(np.abs(rv-cv))/scale)
def feature_signals(reference,current,names=None):
    r,c=np.asarray(reference,float),np.asarray(current,float);names=list(names or [f"feature_{i}" for i in range(r.shape[1])]);return [{"feature":n,"psi":psi(r[:,i],c[:,i]),"wasserstein":normalized_wasserstein(r[:,i],c[:,i])} for i,n in enumerate(names)]
