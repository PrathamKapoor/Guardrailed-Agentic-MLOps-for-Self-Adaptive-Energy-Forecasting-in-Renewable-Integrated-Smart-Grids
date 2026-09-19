import json
from pathlib import Path
from datetime import datetime,timezone
from uuid import uuid4
def make_event(**kwargs):return {"event_id":str(uuid4()),"timestamp":datetime.now(timezone.utc).isoformat(),**kwargs}
def append_event(path:Path,event):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("a",encoding="utf-8") as f:f.write(json.dumps(event,sort_keys=True)+"\n")
