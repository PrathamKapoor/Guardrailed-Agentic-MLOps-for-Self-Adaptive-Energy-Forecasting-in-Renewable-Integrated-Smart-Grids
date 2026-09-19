#!/usr/bin/env python3
"""Phase 19 runner: authorized final-test evaluation of the frozen comparison plan.

Execution requires the frozen plan checksum to verify. The locked test partition
is accessed exclusively under AccessMode.FINAL_EVALUATION with
configuration_frozen=True inside smartgrid_mlops.final_evaluation.engine.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from smartgrid_mlops.experimental_design.protocol import AccessMode  # noqa: F401 (authorization contract reference)
from smartgrid_mlops.final_evaluation.engine import evaluate_plan, write_results
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stderr,
)
LOGGER = logging.getLogger(__name__)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 19 frozen-plan final-test evaluation.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--execute", action="store_true", help="full authorized evaluation")
    group.add_argument("--smoke", action="store_true", help="reduced plumbing check (NON_EVIDENCE)")
    parser.add_argument("--target", action="append", choices=("load", "wind", "pv"))
    args = parser.parse_args()

    plan_path = ROOT / "artifacts/experimental_design/final_test_comparison_plan.yaml"
    LOGGER.info("=== PHASE 19 FINAL-TEST EVALUATION ===")
    LOGGER.info(f"mode                 : {'SMOKE (NON_EVIDENCE_SMOKE)' if args.smoke else 'EXECUTE (FINAL_EVALUATION_VALID)'}")
    LOGGER.info(f"access mode          : {AccessMode.FINAL_EVALUATION.value} (configuration_frozen=True)")
    LOGGER.info(f"frozen plan          : {plan_path.name}")
    LOGGER.info(f"plan sha256          : {_sha256(plan_path)}")

    targets = tuple(args.target or ("load", "wind", "pv"))
    results = evaluate_plan(ROOT, targets=targets, smoke=args.smoke)

    destination = ROOT / "artifacts/experiments/final_evaluation/phase_19" / (
        "smoke" if args.smoke else "official"
    )
    summary = write_results(ROOT, results, destination)

    if not args.smoke:
        metrics_csv = destination / "metrics" / "final_test_metrics.csv"
        research_table = ROOT / "artifacts/research_tables/final_test_comparison_results.csv"
        research_table.write_text(metrics_csv.read_text(encoding="utf-8"), encoding="utf-8")

        from smartgrid_mlops.mlops.tracking import TrackingConfig, tracked_run

        config = TrackingConfig(project_root=ROOT)
        dataset_manifest_sha = _sha256(ROOT / "data/manifests/processed_dataset_manifest.yaml")
        for target in targets:
            entry = results["targets"][target]
            params = {
                "phase": "19",
                "target": target,
                "horizon": 24,
                "reference_model": entry["reference_model"],
                "challenger_model": entry["challenger_model"],
                "baseline_comparator": entry["baseline_comparator"],
                "feature_set_version": "combined_v1",
                "dataset_manifest_sha256": dataset_manifest_sha,
                "frozen_plan_sha256": _sha256(plan_path),
                "configuration_frozen": True,
            }
            tags = {
                "evidence_status": "FINAL_EVALUATION_VALID",
                "final_test_performance_access": "AUTHORIZED_FROZEN_PLAN_EXECUTION",
            }
            with tracked_run(
                config,
                "smartgrid/phase19/final-test-evaluation",
                tags=tags,
                params=params,
                run_name=f"P19-{target}-final-evaluation",
            ) as run:
                for name, block in entry["metrics"].items():
                    for metric_name, value in block.items():
                        if isinstance(value, (int, float)):
                            import mlflow

                            mlflow.log_metric(f"{name}_{metric_name}", float(value))
                primary = entry["tests_raw"].get(f"FT-H1-{target.upper()}")
                if primary:
                    import mlflow

                    mlflow.log_metric("primary_dm_statistic", float(primary["dm_statistic"]))
                    mlflow.log_metric("primary_p_value", float(primary["p_value"]))
                mlflow.log_artifact(str(destination / "metrics" / "summary.json"))
                summary["targets"][target]["mlflow_run_id"] = run.info.run_id

    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
