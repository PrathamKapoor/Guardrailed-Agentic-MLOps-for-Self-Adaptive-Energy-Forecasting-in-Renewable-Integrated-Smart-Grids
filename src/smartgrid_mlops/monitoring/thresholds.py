import json,hashlib
from pathlib import Path
import numpy as np
from .feature_drift import normalized_wasserstein
def calibrate(reference_blocks,percentile=99.0):
    stats={}
    for target,blocks in reference_blocks.items():
        base=np.asarray(blocks[0]);vals=[float(normalized_wasserstein(base,np.asarray(b))) for b in blocks[1:]];stats[target]={"feature_wasserstein":float(np.percentile(vals or [0.0],percentile)),"percentile":percentile,"window_hours":168,"stride_hours":24,"reference_period":"F01-F03"}
    return {"schema_version":"phase14-threshold-v1","thresholds":stats}
def write_freeze(obj,path:Path):
    text=json.dumps(obj,sort_keys=True,indent=2)+"\n";path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text,encoding="utf-8");return hashlib.sha256(text.encode()).hexdigest()
