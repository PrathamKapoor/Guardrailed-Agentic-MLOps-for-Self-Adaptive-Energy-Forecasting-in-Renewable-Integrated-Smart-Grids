#!/usr/bin/env python3
"""Phase 18 ablation runner: deterministic vs bounded agentic MLOps; no model changes, no final-test option."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from smartgrid_mlops.agentic_evaluation.reporting import write_figures, write_tables
from smartgrid_mlops.agentic_evaluation.runner import run_comparison
from smartgrid_mlops.agentic_evaluation.validation import assert_no_model_changes, snapshot_protected
import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stderr,
)
LOGGER = logging.getLogger(__name__)

OUT = ROOT / "artifacts/agentic_evaluation/phase_18"


def dump(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Phase 18 deterministic vs bounded agentic comparison")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--scenario", choices=("D01", "D02", "D03", "D04", "D05", "D06", "D07", "D08"))
    args = parser.parse_args()
    if not (args.all or args.scenario):
        parser.error("select --all or --scenario <Dxx>")
    baseline = snapshot_protected(ROOT)
    scenarios = [args.scenario] if args.scenario else None
    results = run_comparison(ROOT, scenarios=scenarios)
    assert_no_model_changes(ROOT, baseline)
    dump(OUT / "comparison_results.json", results)
    if args.all:
        write_tables(ROOT, results)
        write_figures(ROOT, results)
    summary = results["summary"]
    print(json.dumps({"scenarios": summary["consistency"]["scenarios"],
                      "lifecycle_decision_difference": summary["consistency"]["lifecycle_decision_difference"],
                      "efficiency_improvement_percent": summary["efficiency"]["total_efficiency_improvement_percent"],
                      "governance_violations": summary["safety"]["governance_violations"],
                      "agent_quality_checks_passed": summary["agent_quality_checks"]["passed"],
                      "success_criteria_met": summary["success_criteria_met"]}, indent=2))


if __name__ == "__main__":
    main()
