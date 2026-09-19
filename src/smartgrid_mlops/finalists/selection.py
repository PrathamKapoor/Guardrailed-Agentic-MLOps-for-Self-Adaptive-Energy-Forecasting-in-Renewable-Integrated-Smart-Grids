from __future__ import annotations
def choose_reference(candidates, tie_percent=0.5):
    best=min(x['mae'] for x in candidates); eligible=[x for x in candidates if 100*(x['mae']-best)/best<=tie_percent]
    return min(eligible,key=lambda x:(x['feature_count'],x['complexity'],x['runtime'],x['candidate_id']))
def holm(pvalues):
    order=sorted(range(len(pvalues)),key=lambda i:pvalues[i]); out=[0.0]*len(pvalues); prev=0
    n=len(pvalues)
    for rank,i in enumerate(order): prev=max(prev,min(1,pvalues[i]*(n-rank)));out[i]=prev
    return out
