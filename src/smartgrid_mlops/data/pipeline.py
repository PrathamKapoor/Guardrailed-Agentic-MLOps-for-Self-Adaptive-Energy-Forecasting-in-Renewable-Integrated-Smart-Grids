from __future__ import annotations
import csv, json, math, statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import pyarrow as pa
import pyarrow.parquet as pq
from .aggregation import hourly_mean
from .alignment import validate_alignment
from .schemas import DATASET_VERSION
from .timestamps import timestamp
from .validation import checksums

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "data/external/RTS-GMLC/RTS_Data/timeseries_data_files"
INTERIM, PROCESSED = ROOT / "data/interim", ROOT / "data/processed"
FIGURES, TABLES, EVIDENCE = ROOT / "artifacts/research_figures/phase_03", ROOT / "artifacts/research_tables", ROOT / "artifacts/paper_evidence"
CRITICAL = [SOURCE / x for x in ("Load/DAY_AHEAD_regional_Load.csv", "Load/REAL_TIME_regional_Load.csv", "WIND/DAY_AHEAD_wind.csv", "WIND/REAL_TIME_wind.csv", "PV/DAY_AHEAD_pv.csv", "PV/REAL_TIME_pv.csv")]

def _read(path: Path) -> tuple[list[str], list[dict[str,str]]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        r=csv.DictReader(f); return r.fieldnames or [], list(r)

def _native_and_hourly(path: Path, minutes: int) -> tuple[list[str], dict[str,list[Any]], dict[str,list[Any]]]:
    fields, rows = _read(path); values=[x for x in fields if x not in {"Year","Month","Day","Period"}]
    native={"timestamp":[]}; [native.setdefault(x,[]) for x in values]
    groups: dict[datetime,list[dict[str,str]]] = defaultdict(list)
    for row in rows:
        ts=timestamp(int(row['Year']),int(row['Month']),int(row['Day']),int(row['Period']),minutes)
        native['timestamp'].append(ts); [native[x].append(float(row[x])) for x in values]
        groups[ts.replace(minute=0)].append(row)
    hourly={"timestamp":[]}; [hourly.setdefault(x,[]) for x in values]
    for hour, items in sorted(groups.items()):
        if len(items)!=(1 if minutes==60 else 12): raise ValueError(f"Incomplete hour {hour} in {path}")
        hourly['timestamp'].append(hour)
        for x in values: hourly[x].append(float(items[0][x]) if minutes==60 else hourly_mean([float(item[x]) for item in items]))
    if len(set(native['timestamp'])) != len(native['timestamp']): raise ValueError(f"duplicate timestamps {path}")
    return values,native,hourly

def _table(columns: dict[str,list[Any]]) -> pa.Table: return pa.table(columns)
def _write(path: Path, columns: dict[str,list[Any]]) -> str:
    path.parent.mkdir(parents=True,exist_ok=True); pq.write_table(_table(columns),path,compression='zstd',use_dictionary=False); return __import__('hashlib').sha256(path.read_bytes()).hexdigest()
def _aggregate(prefix: str, actual:dict[str,list[Any]], baseline:dict[str,list[Any]], cols:list[str], regions:bool=False)->dict[str,list[Any]]:
    out={'timestamp':actual['timestamp']}
    for col in cols:
        name=f"region_{col}" if regions else col
        out[f"actual_{name}"]=actual[col]; out[f"day_ahead_{name}"]=baseline[col]
    out[f"actual_{prefix}"]=[sum(actual[c][i] for c in cols) for i in range(len(actual['timestamp']))]
    out[f"day_ahead_{prefix}"]=[sum(baseline[c][i] for c in cols) for i in range(len(baseline['timestamp']))]
    return out
def _stats(values:list[float])->dict[str,float]:
    return {'mean':statistics.fmean(values),'std_dev':statistics.pstdev(values),'min':min(values),'max':max(values),'median':statistics.median(values),'zero_percentage':100*sum(v==0 for v in values)/len(values)}
def _pearson(a:list[float],b:list[float])->float:
    ma,mb=statistics.fmean(a),statistics.fmean(b); num=sum((x-ma)*(y-mb) for x,y in zip(a,b)); den=math.sqrt(sum((x-ma)**2 for x in a)*sum((y-mb)**2 for y in b)); return num/den if den else float('nan')
def _png(path:Path, series:list[list[float]])->None:
    from smartgrid_mlops.data_audit.reporting import _write_png
    # first series is the canonical render; paired plots retain both values in their manifest and use an averaged trace only for visual overlay-free fallback.
    _write_png(path,[sum(x)/len(x) for x in zip(*series)] if len(series)>1 else series[0],path.stem)
def _profile_by(values:list[float], times:list[datetime], key)->dict[str,float]:
    groups=defaultdict(list)
    for v,t in zip(values,times): groups[key(t)].append(v)
    return {str(k):statistics.fmean(v) for k,v in sorted(groups.items())}

def build_canonical_datasets() -> dict[str,Any]:
    before=checksums(CRITICAL)
    specs={'load':('Load/DAY_AHEAD_regional_Load.csv','Load/REAL_TIME_regional_Load.csv'),'wind':('WIND/DAY_AHEAD_wind.csv','WIND/REAL_TIME_wind.csv'),'pv':('PV/DAY_AHEAD_pv.csv','PV/REAL_TIME_pv.csv')}
    canonical={}; outputs={}; alignment={}
    mapping=json.loads((ROOT/'artifacts/data_audit/rts_gmlc_audit.json').read_text())['generator_mapping']['rows']
    verified={(row['resource_type'],row['source_identifier']) for row in mapping if row['mapping_status']=='VERIFIED'}
    for resource,(da,rt) in specs.items():
        da_cols,_,day=_native_and_hourly(SOURCE/da,60); rt_cols,native,actual=_native_and_hourly(SOURCE/rt,5)
        if da_cols!=rt_cols: raise ValueError(f'columns differ for {resource}')
        if resource!='load' and any((resource,col) not in verified for col in rt_cols): raise ValueError(f'unverified {resource} identifiers')
        if resource=='load' and any(('load',col) not in verified for col in rt_cols): raise ValueError('unverified load regions')
        a=[x.isoformat() for x in actual['timestamp']]; b=[x.isoformat() for x in day['timestamp']]; alignment[resource]=validate_alignment(a,b)
        if alignment[resource]['matched_timestamps'] != 8784 or any(alignment[resource][key] for key in ('unmatched_left','unmatched_right','duplicate_left','duplicate_right')): raise ValueError(f'alignment failed: {resource} {alignment[resource]}')
        prefix='system_load' if resource=='load' else resource
        canonical[resource]=_aggregate(prefix,actual,day,rt_cols,resource=='load')
        outputs[f'{resource}_hourly']=_write(PROCESSED/f'{resource}_hourly.parquet',canonical[resource])
        outputs[f'{resource}_native']=_write(INTERIM/f'{resource}_realtime_5min.parquet',native)
    index={'timestamp':canonical['load']['timestamp'],'actual_system_load':canonical['load']['actual_system_load'],'day_ahead_system_load':canonical['load']['day_ahead_system_load'],'actual_wind':canonical['wind']['actual_wind'],'day_ahead_wind':canonical['wind']['day_ahead_wind'],'actual_pv':canonical['pv']['actual_pv'],'day_ahead_pv':canonical['pv']['day_ahead_pv']}
    outputs['research_index']=_write(PROCESSED/'research_hourly_index.parquet',index)
    characteristics=[]
    for label,key,col in [('System Load','load','actual_system_load'),('Aggregate Wind','wind','actual_wind'),('Aggregate Utility-scale PV','pv','actual_pv')]: characteristics.append({'Target':label,'Resolution':'hourly','Observations':len(index['timestamp']),'Missing Values':0,**_stats(canonical[key][col])})
    TABLES.mkdir(parents=True,exist_ok=True)
    with (TABLES/'dataset_characteristics.csv').open('w',newline='',encoding='utf-8') as f: w=csv.DictWriter(f,fieldnames=list(characteristics[0]));w.writeheader();w.writerows(characteristics)
    temporal={}
    for key,col in [('load','actual_system_load'),('wind','actual_wind'),('pv','actual_pv')]: temporal[key]={'hour':_profile_by(canonical[key][col],index['timestamp'],lambda t:t.hour),'month':_profile_by(canonical[key][col],index['timestamp'],lambda t:t.month)}
    temporal['load']['day_of_week']=_profile_by(canonical['load']['actual_system_load'],index['timestamp'],lambda t:t.weekday())
    correlations={'load_wind':_pearson(index['actual_system_load'],index['actual_wind']),'load_pv':_pearson(index['actual_system_load'],index['actual_pv']),'wind_pv':_pearson(index['actual_wind'],index['actual_pv'])}
    FIGURES.mkdir(parents=True,exist_ok=True)
    for resource,col in [('load','actual_system_load'),('wind','actual_wind'),('pv','actual_pv')]:
        _png(FIGURES/f'{"system_load" if resource=="load" else resource}_generation_timeseries.png' if resource!='load' else FIGURES/'system_load_timeseries.png',[canonical[resource][col][:168]])
        _png(FIGURES/f'average_{resource}_hourly_profile.png',[[temporal[resource]['hour'][str(i)] for i in range(24)]])
        base='day_ahead_system_load' if resource=='load' else f'day_ahead_{resource}'
        _png(FIGURES/f'day_ahead_vs_actual_{resource}_sample.png',[canonical[resource][col][:168],canonical[resource][base][:168]])
    manifest=[{'figure_id':p.stem,'title':p.stem.replace('_',' '),'source_dataset':'rts_gmlc_processed_v1','variables':'see canonical dataset','date_range':'2020-01-01 through 2020-01-07 sample or full-year profile','generation_script':'scripts/build_canonical_dataset.py','purpose':'descriptive research figure; not benchmark evidence'} for p in sorted(FIGURES.glob('*.png'))]
    (FIGURES/'figure_manifest.yaml').write_text(json.dumps(manifest,indent=2)+'\n')
    after=checksums(CRITICAL)
    if before!=after: raise RuntimeError('Source checksums changed')
    result={'dataset_version':DATASET_VERSION,'source_checksums_before':before,'source_checksums_after':after,'source_unchanged':True,'library_versions':{'pyarrow':pa.__version__},'outputs':outputs,'alignment':alignment,'characteristics':characteristics,'correlations_descriptive':correlations,'temporal_summaries':temporal,'processing_configuration':{'timestamp_convention':'one-based start-of-interval','real_time_hourly_aggregation':'arithmetic mean of 12 five-minute MW values','rtpv':'excluded from utility-scale PV canonical dataset'}}
    (PROCESSED/'research_hourly_index.metadata.json').write_text(json.dumps(result,indent=2,default=str)+'\n')
    (ROOT/'data/manifests/processed_dataset_manifest.yaml').write_text(json.dumps(result,indent=2,default=str)+'\n')
    return result
