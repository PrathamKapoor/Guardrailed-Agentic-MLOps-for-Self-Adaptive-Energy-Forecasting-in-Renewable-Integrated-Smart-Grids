import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
def test_feature_manifest_and_day_ahead_exclusion():
 m=json.loads((ROOT/'data/manifests/feature_manifest.yaml').read_text());assert len(m['entries'])==6 and m['day_ahead_input']=='forbidden'
def test_h24_origin_contract():
 import pyarrow.parquet as pq
 t=pq.read_table(ROOT/'data/processed/features/load/h24/combined_v1.parquet').to_pydict();assert all(a>b for a,b in zip(t['target_timestamp'],t['forecast_origin'])) and not any('ahead' in x for x in t)
def test_deterministic_feature_build():
 from smartgrid_mlops.features.pipeline import build_features
 assert build_features('load',24)['usable_observations']==8592
