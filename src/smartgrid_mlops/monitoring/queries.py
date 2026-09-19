import json
from pathlib import Path
def get_recent_drift_events(path:Path,target:str):
    if not path.exists():return []
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x and json.loads(x).get("target")==target]
def get_latest_severity(path:Path,target:str):
    e=get_recent_drift_events(path,target);return e[-1].get("severity","NONE") if e else "NONE"
