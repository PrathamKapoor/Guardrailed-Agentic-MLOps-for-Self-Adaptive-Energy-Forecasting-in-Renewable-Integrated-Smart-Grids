#!/usr/bin/env python3
"""Run the deterministic, read-only RTS-GMLC Phase 2 forensic audit."""
from __future__ import annotations
from _scriptlog import get_logger  # scripts/_scriptlog.py: stdout logging, SMARTGRID_MLOPS_LOG_LEVEL
log = get_logger('audit_rts_gmlc')


import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from smartgrid_mlops.data_audit import run_audit  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", action="store_true", help="Profile and print a concise summary without writing audit artifacts.")
    args = parser.parse_args()
    audit = run_audit(summary=args.summary)
    profiles = [*audit["load"].values(), *audit["wind"].values(), *audit["pv"].values(), *audit["rtpv"].values()]
    log.info('RTS-GMLC Phase 2 Audit')
    log.info(f"Source files unchanged: {('PASS' if audit['data_quality']['source_unchanged'] else 'FAIL')}")
    log.info(f'Time-series files profiled: {len(profiles)}')
    log.info(f"Mapping status: {audit['generator_mapping']['status_counts']}")
    log.info('Primary targets: System total load; aggregate wind; aggregate utility-scale PV')
    if args.summary:
        log.info('Summary mode: no audit artifacts written.')
    else:
        log.info('Artifacts: artifacts/data_audit/')
    return 0 if audit["data_quality"]["source_unchanged"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
