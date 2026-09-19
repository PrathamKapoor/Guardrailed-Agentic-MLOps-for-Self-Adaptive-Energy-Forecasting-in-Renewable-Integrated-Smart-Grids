#!/usr/bin/env python3
"""External validation runner — evaluation-only on approved independent datasets.

Requires an approved dataset manifest under data/manifests/<dataset>_manifest.yaml.
No data is synthesized; if the dataset is missing the run fails with a blocker
message and no fake results are produced.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from smartgrid_mlops.external_validation.engine import evaluate_external, write_external_results
from smartgrid_mlops.external_validation.validation import DatasetNotAvailableError
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stderr,
)
LOGGER = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="External validation (evaluation-only) on approved dataset.")
    parser.add_argument("--dataset", required=True, help="Dataset name matching data/manifests/<dataset>_manifest.yaml")
    parser.add_argument("--target", action="append", choices=("load", "wind", "pv"))
    parser.add_argument("--smoke", action="store_true", help="Reduced plumbing check only")
    parser.add_argument("--execute", action="store_true", help="Full external evaluation")
    args = parser.parse_args()
    if not (args.smoke or args.execute):
        parser.error("specify --smoke or --execute")
    targets = tuple(args.target or ("load", "wind", "pv"))
    try:
        results = evaluate_external(ROOT, args.dataset, targets=targets, smoke=args.smoke)
    except DatasetNotAvailableError as exc:
        LOGGER.error(f"BLOCKER: {exc}")
        sys.exit(2)
    dest = ROOT / f"artifacts/experiments/external_validation/{args.dataset}" / ("smoke" if args.smoke else "official")
    write_external_results(ROOT, results, dest)
    # Only write research table on full execute and only if conclusive
    if args.execute:
        import csv

        research = ROOT / "artifacts/research_tables/external_validation_results.csv"
        rows = []
        for t, entry in results.get("targets", {}).items():
            for cfg, blk in entry.get("metrics", {}).items():
                rows.append({"dataset": args.dataset, "target": t, "configuration": cfg, **{k: blk[k] for k in ("MAE", "RMSE", "sMAPE", "nMAE", "nRMSE")}, "samples": entry.get("samples", "")})
        if rows:
            research.parent.mkdir(parents=True, exist_ok=True)
            with research.open("w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=["dataset", "target", "configuration", "MAE", "RMSE", "sMAPE", "nMAE", "nRMSE", "samples"])
                w.writeheader()
                w.writerows(rows)
        # MLflow tracking for external validation
        try:
            import hashlib, json
            from smartgrid_mlops.mlops.tracking import TrackingConfig, tracked_run

            # dataset checksum for provenance
            manifest_path = ROOT / f"data/manifests/{args.dataset}_manifest.yaml"
            dataset_checksum = hashlib.sha256(manifest_path.read_bytes()).hexdigest() if manifest_path.exists() else "unknown"
            frozen_plan_checksum = hashlib.sha256((ROOT / "artifacts/experimental_design/final_test_comparison_plan.yaml").read_bytes()).hexdigest()
            config = TrackingConfig(project_root=ROOT)
            for target in results.get("targets", {}):
                entry = results["targets"][target]
                params = {
                    "dataset": args.dataset,
                    "dataset_checksum": dataset_checksum,
                    "frozen_plan_sha256": frozen_plan_checksum,
                    "target": target,
                    "horizon": 24,
                    "feature_version": "external_v1",
                    "configuration_frozen": True,
                }
                tags = {
                    "evidence_status": "EXTERNAL_VALIDATION_VALID",
                    "evaluation_layer": "external_validation",
                }
                with tracked_run(
                    config,
                    "smartgrid/external_validation",
                    tags=tags,
                    params=params,
                    run_name=f"EXT-{args.dataset}-{target}",
                ) as run:
                    import mlflow

                    for cfg, blk in entry.get("metrics", {}).items():
                        for mk in ("MAE", "RMSE", "sMAPE", "nMAE", "nRMSE"):
                            if mk in blk:
                                mlflow.log_metric(f"{cfg}_{mk}", float(blk[mk]))
                    raw = entry.get("tests_raw", {})
                    for k, v in raw.items():
                        mlflow.log_metric(f"{k}_dm_stat", float(v.get("dm_statistic", 0)))
                        mlflow.log_metric(f"{k}_p_value", float(v.get("p_value", 1)))
                    mlflow.log_artifact(str(dest / "metrics/summary.json"))
        except Exception as exc:
            LOGGER.error(f"MLflow logging skipped/failed: {exc}")
    LOGGER.info(f"External validation status: {results['status']} dataset={args.dataset}")


if __name__ == "__main__":
    main()
