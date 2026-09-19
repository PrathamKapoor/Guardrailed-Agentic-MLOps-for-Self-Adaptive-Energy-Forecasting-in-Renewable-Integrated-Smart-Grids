#!/usr/bin/env python3
r"""Stage 13 CLI: write governance-compatible candidate evidence
packages for the seven Stage 10 / Stage 11 candidates.

This script is PACKAGING ONLY. It does NOT modify the frozen Phase 13
policy, the governance engine, the agent firewall, the registry, or
any protected v1 artefact. It does NOT promote a model or deploy a
model. The only mutation is writing the candidate package files under
`artifacts/v2/governance_candidate_packages/`.

Usage:
  .venv\Scripts\python.exe scripts\run_governance_candidate_packaging.py
"""
from __future__ import annotations
import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from smartgrid_mlops.research_v2.governance_candidate_packages import (
    V2_ROOT, run_all_packages,
)
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stderr,
)
LOGGER = logging.getLogger(__name__)


def main() -> int:
    p = argparse.ArgumentParser(
        description="Stage 13: governance-compatible candidate packaging. "
                    "READ-ONLY on the v1 tree; writes only under "
                    "artifacts/v2/governance_candidate_packages/.")
    p.add_argument("--out-dir", default=None,
                   help="Override the v2 output directory.")
    args = p.parse_args()

    out_dir = Path(args.out_dir).resolve() if args.out_dir else None
    if out_dir is not None:
        # Re-import the module's V2_ROOT to point at the override.
        from smartgrid_mlops.research_v2 import governance_candidate_packages as _pkg
        _pkg.V2_ROOT = out_dir
    summary = run_all_packages()

    LOGGER.info("=" * 72)
    LOGGER.info("STAGE 13 — Governance-Compatible Candidate Packaging")
    LOGGER.info("=" * 72)
    LOGGER.info(f"  n_candidates: {summary['n_candidates']}")
    LOGGER.info()
    LOGGER.info("  CANDIDATE-BY-CANDIDATE SUMMARY:")
    for c in summary["candidates"]:
        LOGGER.info(f"    {c['candidate_id']:50s}  target={c['target']:13s}")
        LOGGER.info(f"      model_spec_fingerprint   : {c['model_spec_fingerprint']}")
        LOGGER.info(f"      feature_spec_fingerprint : {c['feature_spec_fingerprint']}")
        LOGGER.info(f"      benchmark_classification  : {c['benchmark_classification']}")
        LOGGER.info(f"      benchmark_gate_value     : {c['benchmark_gate_value']}")
        LOGGER.info(f"      protocol_compatibility   : {c['protocol_compatibility_classification']}")
    LOGGER.info()
    LOGGER.info(f"  output_root: {V2_ROOT}")
    LOGGER.info()
    LOGGER.info("NO MODEL WAS PROMOTED.")
    LOGGER.info("NO MODEL WAS DEPLOYED.")
    LOGGER.info("STAGE 13 IS GOVERNANCE-EVALUABLE PACKAGING, NOT GOVERNANCE EXECUTION.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
