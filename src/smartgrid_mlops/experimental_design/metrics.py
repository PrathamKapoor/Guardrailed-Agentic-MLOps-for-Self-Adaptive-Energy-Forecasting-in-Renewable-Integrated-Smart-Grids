from __future__ import annotations

import math

def _pairs(actual, predicted):
    a, p = list(actual), list(predicted)
    if not a or len(a) != len(p): raise ValueError("actual and predicted must be non-empty and equal length")
    return a, p

def mae(actual, predicted) -> float:
    a, p = _pairs(actual, predicted); return sum(abs(x-y) for x,y in zip(a,p))/len(a)

def rmse(actual, predicted) -> float:
    a, p = _pairs(actual, predicted); return math.sqrt(sum((x-y)**2 for x,y in zip(a,p))/len(a))

def smape(actual, predicted) -> float:
    """Percentage sMAPE using 200*|a-p|/(|a|+|p|); 0/0 contributes zero."""
    a, p = _pairs(actual, predicted)
    return sum(0.0 if abs(x)+abs(y)==0 else 200*abs(x-y)/(abs(x)+abs(y)) for x,y in zip(a,p))/len(a)

def _normalizer(actual) -> float:
    value = sum(abs(x) for x in actual)/len(actual)
    if value == 0: raise ValueError("mean absolute observed target is zero")
    return value

def nmae(actual, predicted) -> float:
    a, p = _pairs(actual, predicted); return mae(a,p)/_normalizer(a)

def nrmse(actual, predicted) -> float:
    a, p = _pairs(actual, predicted); return rmse(a,p)/_normalizer(a)

def r2(actual, predicted) -> float:
    a, p = _pairs(actual, predicted); mean=sum(a)/len(a); denominator=sum((x-mean)**2 for x in a)
    return 1-sum((x-y)**2 for x,y in zip(a,p))/denominator if denominator else float("nan")
