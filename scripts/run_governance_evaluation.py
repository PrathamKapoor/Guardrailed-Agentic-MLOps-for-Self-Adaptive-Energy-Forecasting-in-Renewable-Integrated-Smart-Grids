#!/usr/bin/env python3
r"""Stage 12 CLI: run the evidence-to-governance evaluation.

This script invokes the Stage 12 orchestrator and prints a brief
summary. It does NOT promote, deploy, or otherwise mutate any
lifecycle state. The only mutation is the append-only audit JSONL
emission under `artifacts/v2/governance_evaluation/stage12_audit.jsonl`.

Usage:
  .venv\Scripts\python.exe scripts\run_governance_evaluation.py

Optional flags:
  --proposed-transition "EXPERIMENTAL -> VALIDATED"
       The lifecycle transition every candidate requests. The default
       is "EXPERIMENTAL -> VALIDATED" (the lowest elevation that
       the frozen Phase 13 transition rules allow for an
       experimental candidate).
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

from smartgrid_mlops.research_v2.governance_evaluation import (
    V2_ROOT, run_governance_evaluation,
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
        description="Stage 12: evidence-to-governance evaluation. "
                    "Reads Stage 10/11 evidence and runs the existing "
                    "frozen Phase 13 GovernanceEngine. READ-ONLY on the "
                    "v1 tree; writes only under artifacts/v2/.")
    p.add_argument("--proposed-transition",
                   default="EXPERIMENTAL -> VALIDATED",
                   help="Lifecycle transition every candidate requests "
                        "(default: EXPERIMENTAL -> VALIDATED).")
    p.add_argument("--out-dir", default=None,
                   help="Override the v2 output directory.")
    args = p.parse_args()

    out_dir = Path(args.out_dir).resolve() if args.out_dir else None
    summary = run_governance_evaluation(
        out_dir=out_dir or V2_ROOT,
        proposed_transition=args.proposed_transition,
    )

    LOGGER.info("=" * 72)
    LOGGER.info("STAGE 12 — Evidence-to-Governance Evaluation")
    LOGGER.info("=" * 72)
    LOGGER.info(f"  policy_id           : {summary['policy_id']}")
    LOGGER.info(f"  policy_version      : {summary['policy_version']}")
    LOGGER.info(f"  policy_checksum     : {summary['policy_checksum']}")
    n_cands = summary['n_candidates_evaluated']
    LOGGER.info(f"  n_candidates        : {n_cands}")
    LOGGER.info(f"  decision_counts     : {summary['decision_counts']}")
    LOGGER.info()
    LOGGER.info("  CANDIDATE-BY-CANDIDATE OUTCOMES:")
    for d in summary["candidate_decisions"]:
        LOGGER.info(f"    {d['candidate_id']:50s}  target={d['target']:12s}  "
              f"decision={d['decision']:8s}  reasons={d['reason_codes']}")
    LOGGER.info()
    LOGGER.info(f"  lifecycle_mutated        : {summary['lifecycle_mutated']}")
    LOGGER.info(f"  registration_state_changed: {summary['registration_state_changed']}")
    LOGGER.info(f"  champion_state_changed   : {summary['champion_state_changed']}")
    LOGGER.info(f"  policy_changed           : {summary['policy_changed']}")
    LOGGER.info()
    LOGGER.info("OUTPUT FILES (all under artifacts/v2/):")
    for f in ("normalized_evidence.json", "candidate_evaluations.json",
              "evidence_gaps.json", "stage12_summary.json",
              "registry_state.json", "stage12_audit.jsonl"):
        path = (out_dir or V2_ROOT) / f
        if path.is_file():
            LOGGER.info(f"    {path.relative_to(ROOT)}")
    LOGGER.info()
    LOGGER.info("NO MODEL WAS PROMOTED.")
    LOGGER.info("NO MODEL WAS DEPLOYED.")
    LOGGER.info("STAGE 12 IS GOVERNANCE EVALUATION, NOT GOVERNANCE EXECUTION.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
