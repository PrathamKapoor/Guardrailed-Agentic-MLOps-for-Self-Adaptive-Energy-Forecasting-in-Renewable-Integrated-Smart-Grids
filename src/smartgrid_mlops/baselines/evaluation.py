from __future__ import annotations

import csv
import hashlib
import json
import platform
import subprocess
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from smartgrid_mlops.experimental_design.metrics import mae, nmae, nrmse, rmse, smape
from smartgrid_mlops.experimental_design.rolling_origin import fold_boundaries

from .base import timestamp_lag_value
from .registry import definitions_for
from .rts_day_ahead import day_ahead_value
from .validation import ensure_identical_timestamps, ensure_validation_only

ROOT = Path(__file__).resolve().parents[3]
TARGET_COLUMNS = {"load": ("load_hourly.parquet", "actual_system_load", "day_ahead_system_load"), "wind": ("wind_hourly.parquet", "actual_wind", "day_ahead_wind"), "pv": ("pv_hourly.parquet", "actual_pv", "day_ahead_pv")}
METRICS = ("MAE", "RMSE", "sMAPE", "nMAE", "nRMSE")


def _metrics(rows: list[dict]) -> dict[str, float]:
    actual, predicted = [r["actual"] for r in rows], [r["prediction"] for r in rows]
    return {"MAE": mae(actual, predicted), "RMSE": rmse(actual, predicted), "sMAPE": smape(actual, predicted), "nMAE": nmae(actual, predicted), "nRMSE": nrmse(actual, predicted)}


def _canonical(target: str) -> tuple[dict, dict]:
    filename, actual_col, day_ahead_col = TARGET_COLUMNS[target]
    rows = pq.read_table(ROOT / "data/processed" / filename, columns=["timestamp", actual_col, day_ahead_col]).to_pylist()
    return ({r["timestamp"]: float(r[actual_col]) for r in rows}, {r["timestamp"]: float(r[day_ahead_col]) for r in rows})


def _eligible(target: str, horizon: int) -> list[dict]:
    path = ROOT / "data/processed/features" / target / f"h{horizon}" / "combined_v1.parquet"
    rows = pq.read_table(path, columns=["forecast_origin", "target_timestamp"]).to_pylist()
    return [r for r in rows if datetime(2020, 1, 1) <= r["target_timestamp"] < datetime(2020, 11, 1)]


def _partition(timestamp: datetime) -> str:
    return "VALIDATION" if timestamp >= datetime(2020, 9, 1) else "ROLLING_ORIGIN"


def _prediction_rows(target: str, horizon: int, definition) -> list[dict]:
    actual_values, day_ahead_values = _canonical(target)
    eligible = _eligible(target, horizon)
    observed_timestamps = [r["target_timestamp"] for r in eligible]
    ensure_identical_timestamps(observed_timestamps, [r["target_timestamp"] for r in eligible])
    results = []
    for row in eligible:
        target_timestamp, origin = row["target_timestamp"], row["forecast_origin"]
        ensure_validation_only(target_timestamp)
        if definition.external:
            prediction = day_ahead_value(day_ahead_values, target_timestamp)
        else:
            prediction, _ = timestamp_lag_value(actual_values, target_timestamp, definition.lag_hours, origin)
        actual = actual_values[target_timestamp]
        results.append({"experiment_id": f"{target.upper()}-H{horizon}-{definition.baseline_id}-DET-ALL", "baseline_id": definition.baseline_id, "target": target, "horizon": horizon, "fold_id": "", "validation_partition": _partition(target_timestamp), "forecast_origin": origin, "target_timestamp": target_timestamp, "actual": actual, "prediction": prediction, "absolute_error": abs(actual-prediction), "squared_error": (actual-prediction)**2, "external_baseline": definition.external})
    return results


def _fold_rows(rows: list[dict], boundary: dict) -> list[dict]:
    return [dict(r, fold_id=boundary["fold_id"], experiment_id=r["experiment_id"].replace("-ALL", f"-{boundary['fold_id']}")) for r in rows if boundary["validation_start"] <= r["target_timestamp"] < boundary["validation_end_exclusive"]]


def _write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields); writer.writeheader(); writer.writerows(rows)


def _markdown(path: Path, title: str, rows: list[dict], fields: list[str]) -> None:
    text = f"# {title}\n\n**Validation results only; final test not accessed.**\n\n| " + " | ".join(fields) + " |\n| " + " | ".join(["---"] * len(fields)) + " |\n"
    text += "".join("| " + " | ".join(f"{r[k]:.6f}" if isinstance(r[k], float) else str(r[k]) for k in fields) + " |\n" for r in rows)
    path.parent.mkdir(parents=True, exist_ok=True); path.write_text(text, encoding="utf-8")


def _sha(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()


def _simple_figures(metrics_rows: list[dict], fold_rows: list[dict]) -> list[Path]:
    from smartgrid_mlops.data_audit.reporting import _write_png
    directory = ROOT / "artifacts/research_figures/phase_06"; directory.mkdir(parents=True, exist_ok=True)
    outputs = []
    for metric, filename in (("MAE", "baseline_mae_comparison_h24.png"), ("RMSE", "baseline_rmse_comparison_h24.png")):
        values = [r[metric] for r in metrics_rows if r["horizon"] == 24]
        p = directory / filename; _write_png(p, values, filename); outputs.append(p)
    for target in ("load", "wind", "pv"):
        values = [r["MAE"] for r in fold_rows if r["target"] == target]
        p = directory / f"baseline_fold_mae_{target}.png"; _write_png(p, values, p.name); outputs.append(p)
    return outputs


def run_baseline_evaluation(targets=("load", "wind", "pv"), horizons=(1, 24)) -> dict:
    output = ROOT / "artifacts/experiments/baselines/phase_06"; predictions_dir = output / "predictions"; metrics_dir = output / "metrics"; manifests_dir = output / "manifests"
    all_predictions, aggregate, folds = [], [], []
    for target in targets:
        for horizon in horizons:
            for definition in definitions_for(horizon):
                rows = _prediction_rows(target, horizon, definition); all_predictions.extend(rows)
                validation = [r for r in rows if r["validation_partition"] == "VALIDATION"]
                aggregate.append({"target": target, "horizon": horizon, "baseline": definition.baseline_id, **_metrics(validation), "external_baseline": definition.external, "samples": len(validation)})
                for boundary in fold_boundaries():
                    subset = _fold_rows(rows, boundary)
                    folds.append({"target": target, "horizon": horizon, "baseline": definition.baseline_id, "fold": boundary["fold_id"], **_metrics(subset), "external_baseline": definition.external, "samples": len(subset)})
    predictions_dir.mkdir(parents=True, exist_ok=True); prediction_path = predictions_dir / "baseline_predictions.parquet"; pq.write_table(pa.Table.from_pylist(all_predictions), prediction_path)
    metric_fields = ["target", "horizon", "baseline", *METRICS, "external_baseline", "samples"]
    fold_fields = ["target", "horizon", "baseline", "fold", *METRICS, "external_baseline", "samples"]
    table_dir = ROOT / "artifacts/research_tables"; report_dir = ROOT / "reports/tables"
    _write_csv(metrics_dir / "baseline_validation_metrics.csv", aggregate, metric_fields); _write_csv(metrics_dir / "baseline_fold_metrics.csv", folds, fold_fields)
    _write_csv(table_dir / "baseline_validation_results.csv", aggregate, metric_fields); _write_csv(table_dir / "baseline_fold_results.csv", folds, fold_fields)
    _markdown(report_dir / "baseline_validation_results.md", "Baseline validation results", aggregate, metric_fields); _markdown(report_dir / "baseline_fold_results.md", "Baseline fold results", folds, fold_fields)
    stability = []
    for key in sorted({(r["target"], r["horizon"], r["baseline"]) for r in folds}):
        values = [r["MAE"] for r in folds if (r["target"], r["horizon"], r["baseline"]) == key]; mean = sum(values)/len(values)
        stability.append({"target": key[0], "horizon": key[1], "baseline": key[2], "mean_validation_MAE": mean, "std_fold_MAE": (sum((v-mean)**2 for v in values)/len(values))**.5, "min_fold_MAE": min(values), "max_fold_MAE": max(values)})
    _write_csv(metrics_dir / "baseline_fold_stability.csv", stability, list(stability[0]))
    figures = _simple_figures(aggregate, folds)
    figure_manifest = [{"figure_id": f"FIG-BL-{i:03d}", "title": p.stem, "target": "multiple" if "comparison" in p.name else p.stem.rsplit("_", 1)[-1], "horizon": 24 if "h24" in p.name else "multiple", "evaluation_period": "development rolling-origin validation; final test excluded", "data_artifact": "artifacts/experiments/baselines/phase_06/metrics", "generation_script": "scripts/run_baseline_experiments.py", "paper_relevance": "Baseline validation comparison or fold stability"} for i, p in enumerate(figures, 1)]
    fig_manifest_path = ROOT / "artifacts/research_figures/phase_06/figure_manifest.yaml"; fig_manifest_path.write_text(json.dumps(figure_manifest, indent=2)+"\n", encoding="utf-8")
    protocol = ROOT / "artifacts/experimental_design/protocol_freeze.yaml"; feature = ROOT / "data/manifests/feature_manifest.yaml"; processed = ROOT / "data/manifests/processed_dataset_manifest.yaml"
    try: commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL).strip()
    except Exception: commit = None
    manifest = {"phase": "06", "protocol_version": json.loads(protocol.read_text())["protocol_version"], "protocol_checksum": _sha(protocol), "dataset_version": json.loads(processed.read_text())["dataset_version"], "processed_dataset_manifest_checksum": _sha(processed), "feature_version": json.loads(feature.read_text())["feature_version"], "feature_manifest_checksum": _sha(feature), "evaluation_period": "rolling-origin folds May-October 2020; aggregate validation September-October 2020", "final_test_accessed": False, "baseline_implementations": [r["baseline"] for r in aggregate], "metric_definitions_version": "config/experiments/metrics.yaml", "code_commit": commit, "execution_environment": {"platform": platform.platform(), "python": sys.version.split()[0]}, "artifact_checksums": {str(p.relative_to(ROOT)): _sha(p) for p in [prediction_path, metrics_dir / "baseline_validation_metrics.csv", metrics_dir / "baseline_fold_metrics.csv", metrics_dir / "baseline_fold_stability.csv", fig_manifest_path]}}
    manifests_dir.mkdir(parents=True, exist_ok=True); manifest_path = output / "baseline_experiment_manifest.yaml"; manifest_path.write_text(json.dumps(manifest, indent=2)+"\n", encoding="utf-8"); (manifests_dir / "baseline_experiment_manifest.yaml").write_text(manifest_path.read_text(), encoding="utf-8")
    return {"predictions": len(all_predictions), "aggregate": aggregate, "folds": folds, "stability": stability, "manifest": manifest}
