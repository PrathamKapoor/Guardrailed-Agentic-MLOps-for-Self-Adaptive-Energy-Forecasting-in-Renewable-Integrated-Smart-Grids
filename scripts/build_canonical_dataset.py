from _scriptlog import get_logger  # scripts/_scriptlog.py: stdout logging, SMARTGRID_MLOPS_LOG_LEVEL
log = get_logger('build_canonical_dataset')
#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from smartgrid_mlops.data import build_canonical_datasets
if __name__=='__main__':
 log.info(f"Canonical dataset build complete: {r['dataset_version']}; aligned rows={r['alignment']['load']['matched_timestamps']}; source unchanged={r['source_unchanged']}")
