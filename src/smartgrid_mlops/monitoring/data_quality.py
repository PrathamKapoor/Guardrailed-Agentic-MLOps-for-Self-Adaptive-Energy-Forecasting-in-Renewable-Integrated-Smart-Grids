import numpy as np
def check_quality(data,expected_columns=None,expected_dtypes=None):
    cols=list(data.columns) if hasattr(data,'columns') else list(range(np.asarray(data).shape[1]));expected_columns=list(expected_columns or cols);missing=[c for c in expected_columns if c not in cols];extra=[c for c in cols if c not in expected_columns];arr=np.asarray(data,dtype=float);return {"missing_columns":missing,"extra_columns":extra,"nan_count":int(np.isnan(arr).sum()),"inf_count":int(np.isinf(arr).sum()),"critical":bool(missing or np.isnan(arr).any() or np.isinf(arr).any())}
