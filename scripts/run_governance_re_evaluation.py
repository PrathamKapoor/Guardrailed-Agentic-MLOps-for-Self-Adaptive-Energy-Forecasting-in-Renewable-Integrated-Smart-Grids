#!/usr/bin/env python3
r"""Stage 14 CLI: governance-compatible candidate re-evaluation.

Reads the Stage 13 candidate packages under
`artifacts/v2/governance_candidate_packages/` and re-evaluates them
through the EXISTING frozen Phase 13 GovernanceEngine. Records
the actual decisions, gate outcomes, and reason codes. Does NOT
promote, deploy, retrain, roll back, or otherwise mutate any
lifecycle state. The only allowed mutation is the append-only audit
JSONL emission via `smartgrid_mlops.governance.audit.audit_decision`.
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

from smartgrid_mlops.governance_re_evaluation import run_reevaluation
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stderr,
)
LOGGER = logging.getLogger(__name__)


def main() -> int:
    p = argparse.ArgumentParser(
        description="Stage 14: governance-compatible candidate "
                    "re-evaluation. Read-only on the v1 tree and the "
                    "Stage 13 packages; writes only under "
                    "artifacts/v2/governance_re_evaluation/.")
    p.add_argument("--packages-root", default=None,
                   help="Override the Stage 13 packages root.")
    p.add_argument("--out-dir", default=None,
                   help="Override the Stage 14 output directory.")
    args = p.parse_args()

    packages_root = (Path(args.packages_root).resolve()
                      if args.packages_root else None)
    out_dir = (Path(args.out_dir).resolve() if args.out_dir
               else None)
    summary = run_reevaluation(packages_root=packages_root, out_dir=out_dir)

    LOGGER.info("=" * 72)
    LOGGER.info("STAGE 14 — Governance-Compatible Candidate Re-Evaluation")
    LOGGER.info("=" * 72)
    LOGGER.info(f"  policy_id           : {summary['policy_id']}")
    LOGGER.info(f"  policy_version      : {summary['policy_version']}")
    LOGGER.info(f"  policy_checksum     : {summary['policy_checksum']}")
    LOGGER.info(f"  policy_fingerprint  : {summary['governance_policy_fingerprint']}")
    LOGGER.info(f"  n_candidates        : {summary['n_candidates_evaluated']}")
    LOGGER.info(f"  n_load_failures     : {summary['n_load_failures']}")
    LOGGER.info(f"  decision_counts     : {summary['decision_counts']}")
    LOGGER.info()
    LOGGER.info("  CANDIDATE-BY-CANDIDATE DECISIONS:")
    for d in summary["decisions"]:
        LOGGER.info(f"    {d['subject_id']:45s}  target={d['target']:13s}")
        LOGGER.info(f"      decision            : {d['decision']}")
        LOGGER.info(f"      proposed_transition : {d['requested_transition']}")
        LOGGER.info(f"      reason_codes        : {d['reason_codes']}")
        LOGGER.info(f"      explanation        : {d['explanation']}")
    LOGGER.info()
    LOGGER.info(f"  audit_path          : {summary['audit_path']}")
    LOGGER.info()
    LOGGER.info("NO MODEL WAS PROMOTED.")
    LOGGER.info("NO MODEL WAS DEPLOYED.")
    LOGGER.info("NO LIFECYCLE STATE WAS EXECUTED.")
    LOGGER.info("STAGE 14 IS GOVERNANCE EVALUATION, NOT GOVERNANCE EXECUTION.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
