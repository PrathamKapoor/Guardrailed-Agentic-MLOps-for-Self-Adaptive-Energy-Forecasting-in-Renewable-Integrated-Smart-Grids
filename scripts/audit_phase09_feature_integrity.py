#!/usr/bin/env python3
"""Metadata-only preservation/audit for P9-DEV-002 (does not read Parquet rows)."""
from __future__ import annotations
from _scriptlog import get_logger  # scripts/_scriptlog.py: stdout logging, SMARTGRID_MLOPS_LOG_LEVEL
log = get_logger('audit_phase09_feature_integrity')
import csv, json, platform, shutil, sys
from datetime import datetime, timezone
from pathlib import Path
import importlib.metadata
import pyarrow.parquet as pq

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from smartgrid_mlops.features.integrity import binary_sha256

OUT=ROOT/'artifacts/integrity/phase_09/p9_dev_002'
MANIFEST=ROOT/'data/manifests/feature_manifest.yaml'

def parquet_metadata(path):
    p=pq.ParquetFile(path); m=p.metadata
    return {'schema':str(p.schema_arrow),'row_count':m.num_rows,'column_count':len(p.schema_arrow),'row_group_count':m.num_row_groups,'created_by':m.created_by,'format_version':m.format_version,'serialized_size':m.serialized_size,'key_value_metadata':m.metadata and {str(k):str(v) for k,v in m.metadata.items()},'compression_codecs':sorted({m.row_group(i).column(j).compression for i in range(m.num_row_groups) for j in range(m.row_group(i).num_columns)})}
def main():
    OUT.mkdir(parents=True,exist_ok=True)
    suspect=ROOT/'data/processed/features/load/h24/combined_v1.parquet'; copy=OUT/'combined_v1_current.parquet'
    if not copy.exists(): shutil.copy2(suspect,copy)
    details={'artifact':str(suspect.relative_to(ROOT)),'audit_copy':str(copy.relative_to(ROOT)),'binary_sha256':binary_sha256(suspect),'file_size':suspect.stat().st_size,'modified_utc':datetime.fromtimestamp(suspect.stat().st_mtime,timezone.utc).isoformat(),**parquet_metadata(suspect)}
    (OUT/'current_artifact_metadata.json').write_text(json.dumps(details,indent=2,default=str)+'\n')
    env=['P9-DEV-002 current environment',f'Python: {sys.version}',f'Platform: {platform.platform()}']
    for package in ('numpy','pandas','pyarrow','scikit-learn','torch'):
        try: env.append(f'{package}: {importlib.metadata.version(package)}')
        except importlib.metadata.PackageNotFoundError: env.append(f'{package}: NOT INSTALLED')
    (OUT/'current_environment.txt').write_text('\n'.join(env)+'\n')
    manifest=json.loads(MANIFEST.read_text()); rows=[]
    for e in manifest['entries']:
        path=ROOT/e['path']; meta=parquet_metadata(path); rows.append({'artifact':e['path'],'manifest_sha256':e['checksum'],'actual_sha256':binary_sha256(path),'match':binary_sha256(path)==e['checksum'],'file_size':path.stat().st_size,'row_count':meta['row_count'],'column_count':meta['column_count']})
    with (ROOT/'artifacts/integrity/phase_09/feature_checksum_audit.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
log.info(rows)
if __name__=='__main__':main()
