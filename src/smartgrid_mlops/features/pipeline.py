from __future__ import annotations
import hashlib,json,math
from datetime import timezone
from pathlib import Path
import pyarrow as pa,pyarrow.parquet as pq
ROOT=Path(__file__).resolve().parents[3]
TARGET={'load':'actual_system_load','wind':'actual_wind','pv':'actual_pv'}
LAGS=(1,24,168); ROLLS=(24,168)
def _sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def build_features(target:str,horizon:int, output_path: Path | None = None):
 if target not in TARGET or horizon not in (1, 6, 12, 24): raise ValueError('target/horizon')
 t=pq.read_table(ROOT/'data/processed/research_hourly_index.parquet').to_pydict(); y=t[TARGET[target]]; ts=t['timestamp']; rows=[]
 maxlook=max(max(LAGS),max(ROLLS)); names=['hour_sin','hour_cos','dow_sin','dow_cos','doy_sin','doy_cos',*[f'lag_{x}' for x in LAGS],*[f'rolling_mean_{x}' for x in ROLLS],'ramp_1h','target']
 for i in range(maxlook,len(y)-horizon):
  o=ts[i]; r={'forecast_origin':o,'target_timestamp':ts[i+horizon],'feature_set_version':f'{target.upper()}_H{horizon}_FULL_V1','target':y[i+horizon]}
  r.update({'hour_sin':math.sin(2*math.pi*o.hour/24),'hour_cos':math.cos(2*math.pi*o.hour/24),'dow_sin':math.sin(2*math.pi*o.weekday()/7),'dow_cos':math.cos(2*math.pi*o.weekday()/7),'doy_sin':math.sin(2*math.pi*o.timetuple().tm_yday/366),'doy_cos':math.cos(2*math.pi*o.timetuple().tm_yday/366)})
  for k in LAGS:r[f'lag_{k}']=y[i-k]
  for w in ROLLS:r[f'rolling_mean_{w}']=sum(y[i-w:i])/w
  r['ramp_1h']=y[i]-y[i-1];rows.append(r)
 out=output_path or ROOT/f'data/processed/features/{target}/h{horizon}/combined_v1.parquet';out=Path(out);out.parent.mkdir(parents=True,exist_ok=True);pq.write_table(pa.Table.from_pylist(rows),out,compression='zstd',use_dictionary=False)
 return {'target':target,'horizon':horizon,'features':names[:-1],'total_observations':len(y),'usable_observations':len(rows),'rows_lost':len(y)-len(rows),'checksum':_sha(out),'path':str(out.relative_to(ROOT))}
def build_all():
 results=[build_features(x,h) for x in TARGET for h in (1,24)]; p=ROOT/'data/manifests/feature_manifest.yaml';p.write_text(json.dumps({'feature_version':'v1','day_ahead_input':'forbidden','global_scaling':'not_applied', 'entries':results},indent=2)+'\n');return results
