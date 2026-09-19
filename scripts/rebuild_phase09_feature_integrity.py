#!/usr/bin/env python3
"""P9-DEV-002 controlled integrity-only reconstruction.

This utility is deliberately isolated from training, HPO, metrics, models, and
prediction code. It prints only hashes, booleans, counts, and metadata.
"""
from __future__ import annotations
import json, math
from pathlib import Path
import sys
import pyarrow.parquet as pq

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from smartgrid_mlops.features.pipeline import build_features, TARGET, LAGS, ROLLS
from smartgrid_mlops.features.integrity import INTEGRITY_AUDIT, binary_sha256, parquet_logical_content_sha256
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stderr,
)
LOGGER = logging.getLogger(__name__)

OUT=ROOT/'artifacts/integrity/phase_09/p9_dev_002'
CURRENT=ROOT/'data/processed/features/load/h24/combined_v1.parquet'
REBUILD1=OUT/'combined_v1_rebuilt.parquet'; REBUILD2=OUT/'combined_v1_rebuilt_2.parquet'

def metadata(path):
 p=pq.ParquetFile(path); m=p.metadata
 return {'created_by':m.created_by,'format_version':m.format_version,'row_group_count':m.num_row_groups,'compression_codecs':sorted({m.row_group(i).column(j).compression for i in range(m.num_row_groups) for j in range(m.row_group(i).num_columns)}),'key_value_metadata_keys':sorted((m.metadata or {}).keys())}
def exact_compare(left,right):
 a=pq.read_table(left); b=pq.read_table(right)
 names_a,names_b=a.schema.names,b.schema.names
 dtypes_a,dtypes_b=[str(x.type) for x in a.schema],[str(x.type) for x in b.schema]
 result={'schema_equal':a.schema==b.schema,'column_names_equal':names_a==names_b,'column_order_equal':names_a==names_b,'dtypes_equal':dtypes_a==dtypes_b,'row_count_equal':a.num_rows==b.num_rows,'column_count_equal':a.num_columns==b.num_columns,'row_order_equal':True,'forecast_origin_equal':True,'target_timestamp_equal':True,'target_equal':True,'feature_values_equal':True,'null_masks_equal':True,'unequal_cell_count':0,'max_absolute_difference':0.0}
 if names_a!=names_b or a.num_rows!=b.num_rows: result.update({'row_order_equal':False,'forecast_origin_equal':False,'target_timestamp_equal':False,'target_equal':False,'feature_values_equal':False}); return result
 for name in names_a:
  av,bv=a[name].to_pylist(),b[name].to_pylist()
  for x,y in zip(av,bv):
   same_null=(x is None)==(y is None)
   if not same_null: result['null_masks_equal']=False
   equal=(x==y) if same_null and x is not None else same_null
   if isinstance(x,float) and isinstance(y,float) and math.isnan(x) and math.isnan(y): equal=True
   if not equal:
    result['unequal_cell_count']+=1
    if isinstance(x,(int,float)) and isinstance(y,(int,float)) and x is not None and y is not None: result['max_absolute_difference']=max(result['max_absolute_difference'],abs(float(x)-float(y)))
  if av!=bv:
   if name in ('forecast_origin','target_timestamp'): result[f'{name}_equal']=False; result['row_order_equal']=False
   elif name=='target': result['target_equal']=False
   else: result['feature_values_equal']=False
 result['values_exactly_equal']=result['unequal_cell_count']==0
 return result
def spot_checks(rebuilt):
 source=pq.read_table(ROOT/'data/processed/research_hourly_index.parquet',columns=['timestamp','actual_system_load']).to_pydict(); ts,y=source['timestamp'],source['actual_system_load']; rows=pq.read_table(rebuilt).to_pylist()
 positions=[0,len(rows)//2,next(i for i,r in enumerate(rows) if r['forecast_origin'].month==2 and r['forecast_origin'].day==29),next(i for i,r in enumerate(rows) if r['forecast_origin'].month==3 and r['forecast_origin'].day==1),len(rows)-1]
 checks=[]
 for pos in positions:
  r=rows[pos]; i=ts.index(r['forecast_origin']); expected={'target':y[i+24],'lag_1':y[i-1],'lag_24':y[i-24],'lag_168':y[i-168],'rolling_mean_24':sum(y[i-24:i])/24,'rolling_mean_168':sum(y[i-168:i])/168,'ramp_1h':y[i]-y[i-1]}
  passed=all(r[k]==v for k,v in expected.items())
  checks.append({'feature_check_name':('first_usable','middle_year','leap_day','month_boundary','last_usable')[len(checks)],'pass':passed,'max_absolute_difference':max([abs(float(r[k])-float(v)) for k,v in expected.items()] or [0.0])})
 return checks
def main():
 OUT.mkdir(parents=True,exist_ok=True)
 # The only permitted final-test read: deterministic LOAD/H24 feature reconstruction.
 build_features('load',24,REBUILD1); build_features('load',24,REBUILD2)
 comp=exact_compare(CURRENT,REBUILD1); comp_rebuilds=exact_compare(REBUILD1,REBUILD2)
 hashes={name:{'binary_sha256':binary_sha256(path),'logical_content_sha256':parquet_logical_content_sha256(path),'metadata':metadata(path)} for name,path in {'current':CURRENT,'rebuilt_1':REBUILD1,'rebuilt_2':REBUILD2}.items()}
 result={'access_mode':INTEGRITY_AUDIT,'integrity_access_reason':'P9-DEV-002','current_vs_rebuilt_1':comp,'rebuilt_1_vs_rebuilt_2':comp_rebuilds,'hashes':hashes,'spot_checks':spot_checks(REBUILD1),'no_models_loaded':True,'no_forecasting_metrics_computed':True}
 (OUT/'semantic_comparison.json').write_text(json.dumps(result,indent=2,default=str)+'\n')
 print(json.dumps({'access_mode':INTEGRITY_AUDIT,'current_binary_sha256':hashes['current']['binary_sha256'],'rebuilt_1_binary_sha256':hashes['rebuilt_1']['binary_sha256'],'rebuilt_2_binary_sha256':hashes['rebuilt_2']['binary_sha256'],'current_logical_sha256':hashes['current']['logical_content_sha256'],'rebuilt_1_logical_sha256':hashes['rebuilt_1']['logical_content_sha256'],'rebuilt_2_logical_sha256':hashes['rebuilt_2']['logical_content_sha256'],'semantic_equal':comp['values_exactly_equal'],'rebuild_deterministic':comp_rebuilds['values_exactly_equal'],'spot_checks_pass':all(x['pass'] for x in result['spot_checks'])},indent=2))
if __name__=='__main__': main()
