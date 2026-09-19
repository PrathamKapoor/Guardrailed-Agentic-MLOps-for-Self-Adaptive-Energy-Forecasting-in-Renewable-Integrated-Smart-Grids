#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / "src"))
from smartgrid_mlops.baselines.evaluation import run_baseline_evaluation
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stderr,
)
LOGGER = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Phase 6 validation-only deterministic baselines.")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--target", action="append", choices=("load", "wind", "pv"))
    parser.add_argument("--horizon", action="append", type=int, choices=(1, 24))
    parser.add_argument("--validation-only", action="store_true", default=True)
    args = parser.parse_args()
    if not args.all and not args.target and not args.horizon: parser.error("specify --all or a target/horizon selection")
    result = run_baseline_evaluation(tuple(args.target or ("load", "wind", "pv")), tuple(args.horizon or (1, 24)))
    print(json.dumps({"final_test_accessed": False, "prediction_rows": result["predictions"], "validation_result_rows": len(result["aggregate"]), "fold_result_rows": len(result["folds"])}, indent=2))


if __name__ == "__main__": main()
