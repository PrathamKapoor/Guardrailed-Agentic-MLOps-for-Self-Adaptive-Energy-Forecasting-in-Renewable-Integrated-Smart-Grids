#!/usr/bin/env python3
"""Phase 20 dashboard builder: read-only, deterministic.

Consumes Phase 19 artifacts as authoritative sources and emits a self-contained
static site under `dashboard/`:

  dashboard/index.html          (entry point; executive + research)
  dashboard/charts.html          (interactive actual-vs-predicted)
  dashboard/styles.css
  dashboard/app.js
  dashboard/data/results.json    (metrics, model-vs-benchmark, payload)
  dashboard/data/predictions.json (long-format predictions for charts)
  dashboard/data/figures.js      (embedded base64 PNGs/SVG)
  dashboard/data/protocol.json   (frozen plan + protocol + governance facts)
  dashboard/data/lineage.json    (lineage summary)

Inputs (all read-only):
  artifacts/research_tables/final_predictions.csv
  artifacts/research_tables/final_forecasting_results.csv
  artifacts/research_tables/final_model_comparison.csv
  artifacts/audit/phase_19_final_execution_audit.json
  artifacts/mlops/lineage/final_evaluation_lineage_report.md
  artifacts/experimental_design/phase_19_final_evaluation_protocol_freeze.yaml
  artifacts/experimental_design/final_test_comparison_plan.yaml
  artifacts/research_figures/phase_19/*.png, *.svg
  artifacts/ui_build/phase19_integrity_baseline.json
  reports/phase_19_completion.md

This script NEVER writes to any of the above. It only writes under dashboard/.
"""
from __future__ import annotations

from _scriptlog import get_logger  # scripts/_scriptlog.py: stdout logging, SMARTGRID_MLOPS_LOG_LEVEL
log = get_logger('build_dashboard')
import base64
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

DASH = ROOT / "dashboard"
DATA = DASH / "data"

PREDICTIONS_CSV = ROOT / "artifacts/research_tables/final_predictions.csv"
FORECASTING_CSV = ROOT / "artifacts/research_tables/final_forecasting_results.csv"
COMPARISON_CSV = ROOT / "artifacts/research_tables/final_model_comparison.csv"
AUDIT_JSON = ROOT / "artifacts/audit/phase_19_final_execution_audit.json"
LINEAGE_MD = ROOT / "artifacts/mlops/lineage/final_evaluation_lineage_report.md"
PROTOCOL_YAML = ROOT / "artifacts/experimental_design/phase_19_final_evaluation_protocol_freeze.yaml"
PLAN_YAML = ROOT / "artifacts/experimental_design/final_test_comparison_plan.yaml"
INTEGRITY = ROOT / "artifacts/ui_build/phase19_integrity_baseline.json"
COMPLETION_MD = ROOT / "reports/phase_19_completion.md"
FIG_DIR = ROOT / "artifacts/research_figures/phase_19"

TARGET_INFO = {
    "load": {
        "model": "random_forest", "features": ["lag_1", "lag_24", "lag_168"],
        "feature_explanation": {
            "lag_1": "System load one hour before the forecast origin",
            "lag_24": "System load the same hour on the previous day",
            "lag_168": "System load the same hour on the previous week (168 hours = 7 days)",
        },
        "benchmark": "RTS_DAY_AHEAD", "benchmark_explanation": "The published day-ahead forecast observed in the source dataset (day_ahead_system_load column).",
    },
    "wind": {
        "model": "hist_gradient_boosting", "features": ["lag_1", "lag_24", "lag_168"],
        "feature_explanation": {
            "lag_1": "Wind generation one hour before the forecast origin",
            "lag_24": "Wind generation the same hour on the previous day",
            "lag_168": "Wind generation the same hour on the previous week (168 hours = 7 days)",
        },
        "benchmark": "RTS_DAY_AHEAD", "benchmark_explanation": "The published day-ahead forecast observed in the source dataset (day_ahead_wind column).",
    },
    "pv": {
        "model": "random_forest", "features": ["lag_1", "lag_24", "lag_168"],
        "feature_explanation": {
            "lag_1": "PV generation one hour before the forecast origin",
            "lag_24": "PV generation the same hour on the previous day",
            "lag_168": "PV generation the same hour on the previous week (168 hours = 7 days)",
        },
        "benchmark": "H24_DAILY_PERSISTENCE", "benchmark_explanation": "Prediction at hour t = observed actual value at hour t - 24 hours (H24 daily persistence).",
    },
}


def _load(path: Path) -> object:
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".json":
        return json.loads(text)
    if path.suffix in (".yaml", ".yml"):
        import yaml
        return yaml.safe_load(text)
    return text


def _embed_image(p: Path) -> str:
    mime = "image/svg+xml" if p.suffix == ".svg" else "image/png"
    return f"data:{mime};base64,{base64.b64encode(p.read_bytes()).decode('ascii')}"


def build_results() -> dict:
    """Per-target / per-configuration metrics + model-vs-benchmark record."""
    forecasting = list(csv.DictReader(FORECASTING_CSV.open(encoding="utf-8")))
    comparison = list(csv.DictReader(COMPARISON_CSV.open(encoding="utf-8")))
    by_target: dict = {t: {"configurations": {}, "comparison": None} for t in TARGET_INFO}
    for row in forecasting:
        by_target[row["Target"]]["configurations"].setdefault(row["Model"], []).append({
            "configuration": row["Model"],
            "MAE": float(row["MAE"]), "RMSE": float(row["RMSE"]),
            "sMAPE": float(row["sMAPE"]), "nMAE": float(row["nMAE"]), "nRMSE": float(row["nRMSE"]),
        })
    for row in comparison:
        by_target[row["Target"]]["comparison"] = {
            "frozen_model": row["Frozen model"],
            "frozen_model_mae": float(row["Frozen model MAE"]),
            "external_benchmark": row["External benchmark"],
            "benchmark_mae": float(row["Benchmark MAE"]),
            "absolute_difference": float(row["Absolute difference"]),
            "relative_difference_percent": float(row["Relative difference (pct)"]),
        }
    audit = _load(AUDIT_JSON)
    return {"targets": by_target, "evaluation_window": audit["final_test_window"],
            "governance_invariants": audit["governance_invariants"]}


def build_predictions() -> dict:
    """Long-format predictions (timestamp, target, model, prediction, actual, error)."""
    rows = list(csv.DictReader(PREDICTIONS_CSV.open(encoding="utf-8")))
    by_target: dict = {t: [] for t in TARGET_INFO}
    for r in rows:
        pred = float(r["prediction"]); actual = float(r["actual"])
        by_target[r["target"]].append({
            "timestamp": r["timestamp"], "model": r["model"],
            "prediction": pred, "actual": actual,
            "absolute_error": float(r["absolute_error"]),
            "signed_error": pred - actual,
        })
    return {"targets": by_target,
            "counts": {t: len(v) for t, v in by_target.items()},
            "models_per_target": {t: sorted({p["model"] for p in v}) for t, v in by_target.items()}}


def build_protocol() -> dict:
    protocol = _load(PROTOCOL_YAML)
    plan = _load(PLAN_YAML)
    integrity = _load(INTEGRITY)
    return {
        "frozen_models": protocol["frozen_final_models"],
        "frozen_baselines": protocol["frozen_final_baselines"],
        "frozen_features": protocol["frozen_features"],
        "frozen_preprocessing": protocol["frozen_preprocessing"],
        "frozen_final_test_window": protocol["frozen_final_test_window"],
        "frozen_metrics": protocol["frozen_metrics"],
        "statistical_analysis_scope": protocol["statistical_analysis"],
        "outputs_inventory": protocol["outputs"],
        "governance_invariants": protocol["governance_invariants"],
        "agentic_validation": protocol["agentic_validation"],
        "previous_freeze_invariants": protocol["previous_freeze_invariants"],
        "phase_19_plan_matrix": {t: {"reference": plan["matrix"][t]["reference_model"]["candidate_id"],
                                       "challenger": plan["matrix"][t]["challengers"][0]["candidate_id"],
                                       "baseline": plan["matrix"][t]["baseline_comparator"]}
                                  for t in TARGET_INFO},
        "phase_19_plan_status": plan.get("status"),
        "phase_19_protocol_freeze_sha256": integrity["phase_19_protocol_freeze_sha256"],
        "phase_19_protocol_freeze_sidecar": integrity["phase_19_protocol_freeze_sha256"],
        "integrity_baseline_critical_artifact_count": sum(1 for v in integrity.values() if isinstance(v, dict) and v.get("sha256")),
        "target_info": TARGET_INFO,
    }


def build_figures() -> dict:
    mapping = {
        "performance": FIG_DIR / "final_model_performance_comparison.png",
        "error_distribution": FIG_DIR / "final_error_distribution.png",
        "forecast_vs_actual": FIG_DIR / "forecast_vs_actual_plots.png",
        "architecture": FIG_DIR / "system_architecture_final.svg",
    }
    return {k: _embed_image(p) for k, p in mapping.items() if p.exists()}


def build_lineage() -> dict:
    md = LINEAGE_MD.read_text(encoding="utf-8")
    completion = COMPLETION_MD.read_text(encoding="utf-8")
    audit = _load(AUDIT_JSON)
    return {
        "lineage_report_markdown": md,
        "completion_report_markdown": completion,
        "model_fingerprints": audit["model_fingerprints"],
        "feature_fingerprint_source": audit["feature_fingerprint_source"],
        "dataset_fingerprint": audit["dataset_fingerprint"],
        "protocol_versions": audit["protocol_versions"],
        "final_data_access_record": audit["final_data_access_record"],
    }


def main() -> None:
    DASH.mkdir(parents=True, exist_ok=True)
    DATA.mkdir(parents=True, exist_ok=True)
    DATA.joinpath("results.json").write_text(json.dumps(build_results(), indent=2) + "\n", encoding="utf-8")
    DATA.joinpath("predictions.json").write_text(json.dumps(build_predictions(), indent=2) + "\n", encoding="utf-8")
    DATA.joinpath("protocol.json").write_text(json.dumps(build_protocol(), indent=2) + "\n", encoding="utf-8")
    DATA.joinpath("lineage.json").write_text(json.dumps(build_lineage(), indent=2) + "\n", encoding="utf-8")
    figs = build_figures()
    figures_js = "window.EMBEDDED_FIGURES = " + json.dumps(figs) + ";\n"
    DATA.joinpath("figures.js").write_text(figures_js, encoding="utf-8")
    log.info(f'wrote: dashboard/index.html (next step), {len(figs)} figures embedded')
    log.info(f"results target rows: {sum((len(v) for v in build_results()['targets'].values()))}")


if __name__ == "__main__":
    main()
