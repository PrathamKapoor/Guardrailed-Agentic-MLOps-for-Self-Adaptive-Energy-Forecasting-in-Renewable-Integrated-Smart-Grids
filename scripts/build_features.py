from pathlib import Path
import argparse,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from smartgrid_mlops.features.pipeline import build_features,build_all
import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stderr,
)
LOGGER = logging.getLogger(__name__)
p=argparse.ArgumentParser();p.add_argument('--target',choices=['load','wind','pv']);p.add_argument('--horizon',type=int,choices=[1,24]);p.add_argument('--output',type=Path);p.add_argument('--all',action='store_true');a=p.parse_args()
if a.all: LOGGER.info(build_all())
elif a.target and a.horizon: LOGGER.info(build_features(a.target,a.horizon,a.output))
else:p.error('use --all or --target and --horizon')
