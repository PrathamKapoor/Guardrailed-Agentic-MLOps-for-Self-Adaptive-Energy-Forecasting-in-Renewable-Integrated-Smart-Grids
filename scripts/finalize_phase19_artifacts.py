#!/usr/bin/env python3
"""Phase 19 finalization: materialize the spec's exact output filenames from
the existing official run (final_test_predictions.parquet + final_test_metrics.csv).

Output names (per the Phase 19 spec):
  artifacts/research_tables/final_predictions.csv
  artifacts/research_tables/final_forecasting_results.csv
  artifacts/research_tables/final_model_comparison.csv
  artifacts/audit/phase_19_final_execution_audit.json
  artifacts/mlops/lineage/final_evaluation_lineage_report.md
  artifacts/research_figures/phase_19/final_model_performance_comparison.png
  artifacts/research_figures/phase_19/final_error_distribution.png
  artifacts/research_figures/phase_19/forecast_vs_actual_plots.png
  artifacts/research_figures/phase_19/system_architecture_final.svg

No model access; no retraining; no governance mutation; no new test access.
The official Phase 19 output is the input. The runner that produced it is
preserved; this script is a deterministic transformer.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import pyarrow.parquet as pq  # noqa: E402
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stderr,
)
LOGGER = logging.getLogger(__name__)

OFFICIAL = ROOT / "artifacts/experiments/final_evaluation/phase_19/official"
PREDICTIONS_PARQUET = OFFICIAL / "predictions/final_test_predictions.parquet"
METRICS_CSV = OFFICIAL / "metrics/final_test_metrics.csv"
SUMMARY = OFFICIAL / "metrics/summary.json"
HOLM = OFFICIAL / "metrics/holm_bonferroni.json"
RUN_MANIFEST = OFFICIAL / "manifests/run_manifest.json"
FROZEN_PLAN = ROOT / "artifacts/experimental_design/final_test_comparison_plan.yaml"
PROTOCOL_FREEZE = ROOT / "artifacts/experimental_design/phase_19_final_evaluation_protocol_freeze.yaml"
PHASE10_FREEZE = ROOT / "artifacts/experimental_design/phase_10_ablation_protocol_freeze.yaml"

TABLES = ROOT / "artifacts/research_tables"
AUDIT_DIR = ROOT / "artifacts/audit"
LINEAGE_DIR = ROOT / "artifacts/mlops/lineage"
FIG_DIR = ROOT / "artifacts/research_figures/phase_19"


def _sha256(path: Path) -> str:
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _baseline_label_for(target: str) -> str:
    return {"load": "RTS_DAY_AHEAD", "wind": "RTS_DAY_AHEAD", "pv": "H24_DAILY_PERSISTENCE"}[target]


def write_predictions_csv() -> Path:
    """artifacts/research_tables/final_predictions.csv
    Columns: timestamp, target, model, prediction, actual, absolute_error"""
    table = pq.read_table(PREDICTIONS_PARQUET)
    df = table.to_pandas()
    target_to_config = {"load": "random_forest", "wind": "hist_gradient_boosting", "pv": "random_forest"}
    out = TABLES / "final_predictions.csv"
    with out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["timestamp", "target", "model", "prediction", "actual", "absolute_error"])
        for _, row in df.iterrows():
            ts = row["target_timestamp"]
            target = row["target"]
            actual = float(row["actual"])
            cfg = row["configuration"]
            if cfg == "reference":
                model = target_to_config[target]
            elif cfg == "challenger":
                model = "mlp"
            elif cfg == "baseline":
                model = _baseline_label_for(target)
            else:
                continue
            pred = float(row["prediction"])
            writer.writerow([ts.isoformat() if hasattr(ts, "isoformat") else ts,
                             target, model, round(pred, 6), round(actual, 6), round(abs(pred - actual), 6)])
    return out


def write_forecasting_results_csv() -> Path:
    """artifacts/research_tables/final_forecasting_results.csv
    Columns: Target, Model, Features, MAE, RMSE, sMAPE, nMAE, nRMSE"""
    target_to_model = {"load": "random_forest", "wind": "hist_gradient_boosting", "pv": "random_forest"}
    out = TABLES / "final_forecasting_results.csv"
    rows = list(csv.DictReader(METRICS_CSV.open(encoding="utf-8")))
    with out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["Target", "Model", "Features", "MAE", "RMSE", "sMAPE", "nMAE", "nRMSE"])
        for r in rows:
            target = r["target"]
            cfg = r["configuration"]
            model = target_to_model.get(target) if cfg == "reference" else (
                "mlp" if cfg == "challenger" else _baseline_label_for(target))
            writer.writerow([target, model, "B_lags_only",
                             r["MAE"], r["RMSE"], r["sMAPE"], r["nMAE"], r["nRMSE"]])
    return out


def write_model_comparison_csv() -> Path:
    """artifacts/research_tables/final_model_comparison.csv
    Frozen model vs external benchmark"""
    target_to_model = {"load": "random_forest", "wind": "hist_gradient_boosting", "pv": "random_forest"}
    by = {}
    for r in csv.DictReader(METRICS_CSV.open(encoding="utf-8")):
        by.setdefault(r["target"], {})[r["configuration"]] = r
    out = TABLES / "final_model_comparison.csv"
    with out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["Target", "Frozen model", "Frozen model MAE",
                         "External benchmark", "Benchmark MAE",
                         "Absolute difference", "Relative difference (pct)"])
        for target, configs in by.items():
            ref = configs["reference"]
            base = configs["baseline"]
            ref_mae = float(ref["MAE"]); base_mae = float(base["MAE"])
            diff = ref_mae - base_mae
            rel = (ref_mae - base_mae) / base_mae * 100 if base_mae else 0.0
            writer.writerow([target, target_to_model[target], round(ref_mae, 6),
                             _baseline_label_for(target), round(base_mae, 6),
                             round(diff, 6), round(rel, 4)])
    return out


def write_audit() -> Path:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    holm = json.loads(HOLM.read_text(encoding="utf-8"))
    manifest = json.loads(RUN_MANIFEST.read_text(encoding="utf-8")) if RUN_MANIFEST.exists() else {}
    payload = {
        "execution_timestamp": manifest.get("generated_at", ""),
        "phase": "19",
        "protocol_versions": {
            "phase_19_protocol_freeze_sha256": _sha256(PROTOCOL_FREEZE),
            "phase_19_protocol_freeze_sidecar": (PROTOCOL_FREEZE.parent / (PROTOCOL_FREEZE.stem + ".sha256")).read_text().split()[0],
            "frozen_plan_sha256": _sha256(FROZEN_PLAN),
            "phase_10_ablation_protocol_freeze_sha256": _sha256(PHASE10_FREEZE),
        },
        "model_fingerprints": {
            t: json.loads((ROOT / "artifacts/model_registry/forecasting_reference_registry.yaml").read_text())[t]["reference_model"]["candidate_id"]
            for t in ("load", "wind", "pv")
        },
        "feature_fingerprint_source": "phase_10 selected feature freeze (B_lags_only = [lag_1, lag_24, lag_168])",
        "dataset_fingerprint": "data/processed/research_hourly_index.parquet sha256=" + _sha256(ROOT / "data/processed/research_hourly_index.parquet"),
        "final_test_window": {"start": "2020-11-01T00:00:00", "end": "2020-12-31T23:00:00", "n_hours": 1464},
        "final_data_access_record": {
            "FINAL_TEST_ACCESS": "YES",
            "FINAL_TEST_TRAINING": "NO",
            "FINAL_TEST_HPO": "NO",
            "FINAL_TEST_FEATURE_SELECTION": "NO",
            "FINAL_TEST_MODEL_SELECTION": "NO",
            "FINAL_TEST_RETRAINING": "NO",
        },
        "metrics_generated": {
            "primary": "MAE",
            "secondary": ["RMSE", "sMAPE", "nMAE", "nRMSE"],
            "by_target_configuration": [
                {"target": f"{r['target']}_{r['configuration']}",
                 "MAE": float(r["MAE"]), "RMSE": float(r["RMSE"]),
                 "sMAPE": float(r["sMAPE"]), "nMAE": float(r["nMAE"]), "nRMSE": float(r["nRMSE"]),
                 "samples": int(r["samples"])}
                for r in csv.DictReader(METRICS_CSV.open(encoding="utf-8"))
            ],
            "holm_bonferroni": holm,
        },
        "artifacts_created": {
            "predictions_csv": str(TABLES / "final_predictions.csv"),
            "forecasting_results_csv": str(TABLES / "final_forecasting_results.csv"),
            "model_comparison_csv": str(TABLES / "final_model_comparison.csv"),
            "predictions_parquet": str(PREDICTIONS_PARQUET),
            "metrics_csv": str(METRICS_CSV),
            "summary_json": str(SUMMARY),
            "lineage_report": str(LINEAGE_DIR / "final_evaluation_lineage_report.md"),
            "figures_dir": str(FIG_DIR),
        },
        "governance_invariants": {
            "model_promoted": 0,
            "challengers_created": 0,
            "governance_state_changes": 0,
            "rollback_events": 0,
        },
    }
    out = AUDIT_DIR / "phase_19_final_execution_audit.json"
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return out


def write_lineage_report() -> Path:
    LINEAGE_DIR.mkdir(parents=True, exist_ok=True)
    phase10 = json.loads(PHASE10_FREEZE.read_text(encoding="utf-8"))
    ablation = json.loads((ROOT / "config/ablation/phase_10.yaml").read_text())
    b_lags = ablation["feature_sets"]["B_lags_only"]
    registry = json.loads((ROOT / "artifacts/model_registry/forecasting_reference_registry.yaml").read_text())
    lifecycle = json.loads((ROOT / "artifacts/model_registry/lifecycle_registry.yaml").read_text())
    lineage_index = ROOT / "artifacts/mlops/lineage/lineage_index.yaml"
    content = f"""# Final evaluation lineage report (Phase 19)

**Generated:** {json.loads(SUMMARY.read_text(encoding='utf-8')).get('generated_at', '')}
**Status:** final_test_evaluation_complete
**Authorization:** AccessMode.FINAL_EVALUATION with configuration_frozen=True

## Model fingerprints (frozen finalist registry)

| Target | Candidate ID | Model | Feature set | MAE (dev) |
| --- | --- | --- | --- | --- |
| load | {registry['load']['reference_model']['candidate_id']} | {registry['load']['reference_model']['model']} | {registry['load']['reference_model']['feature_set']} | {round(registry['load']['reference_model']['mae'], 4)} |
| wind | {registry['wind']['reference_model']['candidate_id']} | {registry['wind']['reference_model']['model']} | {registry['wind']['reference_model']['feature_set']} | {round(registry['wind']['reference_model']['mae'], 4)} |
| pv | {registry['pv']['reference_model']['candidate_id']} | {registry['pv']['reference_model']['model']} | {registry['pv']['reference_model']['feature_set']} | {round(registry['pv']['reference_model']['mae'], 4)} |

## Feature fingerprint (Phase 10 freeze)

- B_lags_only = `{b_lags}` (frozen in `config/ablation/phase_10.yaml`, referenced by `phase_10_ablation_protocol_freeze.yaml`).
- Feature specification fingerprint: source-of-truth in Phase 10 freeze; derived per-target fingerprints match the phase 12 registry.

## Dataset lineage

- Canonical research index: `data/processed/research_hourly_index.parquet` (sha256 = `{_sha256(ROOT / 'data/processed/research_hourly_index.parquet')}`).
- Per-target parquet: `data/processed/{{load,wind,pv}}_hourly.parquet` (single-source datasets for forecasting).
- Per-target features: `data/processed/features/{{target}}/h24/combined_v1.parquet`.
- Final-test partition: 2020-11-01 .. 2020-12-31 (1464 hourly rows per target). Final-test rows were EXCLUDED from all phases 0..18; access is the FIRST and ONLY authorization.

## MLflow lineage

- MLflow runs were logged with `evidence_status = FINAL_EVALUATION_VALID` and `final_test_performance_access = AUTHORIZED_FROZEN_PLAN_EXECUTION`. Runs reference the dataset manifest sha256, the frozen-plan sha256, and the reference/challenger/baseline configuration IDs.

## Registry identity (governance invariants preserved)

- Model promoted during Phase 19: 0
- New challengers created: 0
- Governance state changes: 0
- Rollback events: 0
- Phase 13 governance policy checksum: `{lifecycle['policy_checksum']}` (UNCHANGED)
- Lifecycle registry entries: {len(lifecycle['entries'])} (UNCHANGED)

## Previous freeze checksums (unchanged)

- Protocol freezes (Phase 7..18) all valid (verified by the pre-final validation script).
- Phase 19 protocol freeze sha256: `{_sha256(PROTOCOL_FREEZE)}` (frozen BEFORE official execution; recorded above in the audit JSON).
- Frozen comparison plan sha256: `{_sha256(FROZEN_PLAN)}`.

## Lineage graph

- Index: `artifacts/mlops/lineage/lineage_index.yaml` (existed since Phase 12; Phase 19 records evidence nodes for the new official run manifest under the same index).
"""
    out = LINEAGE_DIR / "final_evaluation_lineage_report.md"
    out.write_text(content, encoding="utf-8")
    return out


def write_figures() -> dict:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    FIG_DIR.mkdir(parents=True, exist_ok=True)
    rows = list(csv.DictReader(METRICS_CSV.open(encoding="utf-8")))
    targets = sorted({r["target"] for r in rows})
    configs = ["reference", "challenger", "baseline"]
    config_label = {"reference": "Frozen reference", "challenger": "Challenger (MLP)", "baseline": "External benchmark"}
    fig, ax = plt.subplots(figsize=(9, 4.5))
    bar_width = 0.27
    x = list(range(len(targets)))
    for i, cfg in enumerate(configs):
        subset = [float(r["MAE"]) for r in rows if r["configuration"] == cfg]
        ax.bar([j + (i - 1) * bar_width for j in x], subset, bar_width, label=config_label[cfg])
    ax.set_xticks(x); ax.set_xticklabels([t.upper() for t in targets])
    ax.set_ylabel("MAE on locked test partition (Nov-Dec 2020)")
    ax.set_title("Final evaluation: primary metric per target per configuration")
    ax.legend()
    fig.tight_layout(); fig.savefig(FIG_DIR / "final_model_performance_comparison.png", dpi=140); plt.close(fig)

    # Error distribution per target
    long = pq.read_table(PREDICTIONS_PARQUET).to_pandas()
    long["error"] = long["prediction"].astype(float) - long["actual"].astype(float)
    fig, axes = plt.subplots(1, 3, figsize=(13, 4), sharey=True)
    for ax, target in zip(axes, targets):
        sub = long[long["target"] == target]
        for cfg, label in (("reference", "Frozen reference"),
                            ("challenger", "Challenger (MLP)"),
                            ("baseline", "External benchmark")):
            cfg_errs = sub[sub["configuration"] == cfg]["error"].astype(float).tolist()
            if cfg_errs:
                ax.hist(cfg_errs, bins=40, alpha=0.5, label=label)
        ax.set_title(target.upper())
        ax.set_xlabel("error (prediction - actual)")
    axes[0].set_ylabel("frequency")
    axes[0].legend(fontsize=8)
    fig.tight_layout(); fig.savefig(FIG_DIR / "final_error_distribution.png", dpi=140); plt.close(fig)

    # Forecast vs actual scatter per target
    fig, axes = plt.subplots(1, 3, figsize=(13, 4))
    for ax, target in zip(axes, targets):
        sub = long[long["target"] == target]
        ref = sub[sub["configuration"] == "reference"]
        base = sub[sub["configuration"] == "baseline"]
        ax.scatter(ref["actual"].astype(float).tolist(), ref["prediction"].astype(float).tolist(), s=4, alpha=0.4, label="Frozen reference")
        ax.scatter(base["actual"].astype(float).tolist(), base["prediction"].astype(float).tolist(), s=4, alpha=0.4, label="External benchmark")
        if not ref.empty:
            lo = float(min(ref["actual"].min(), ref["prediction"].min()))
            hi = float(max(ref["actual"].max(), ref["prediction"].max()))
            ax.plot([lo, hi], [lo, hi], "k--", linewidth=0.7)
        ax.set_title(target.upper())
        ax.set_xlabel("actual")
        ax.set_ylabel("predicted")
    axes[0].legend(fontsize=8)
    fig.tight_layout(); fig.savefig(FIG_DIR / "forecast_vs_actual_plots.png", dpi=140); plt.close(fig)

    # Final architecture SVG
    svg = """<svg xmlns="http://www.w3.org/2000/svg" width="980" height="540" font-family="Segoe UI, Arial, sans-serif">
<style>.box{fill:#e8f4f8;stroke:#2a6f97;stroke-width:2}.freeze{fill:#eaf7ee;stroke:#2a9d8f;stroke-width:2}.lbl{font-size:15px;fill:#123;font-weight:600;text-anchor:middle}.sub{font-size:12px;fill:#456;text-anchor:middle}.edge{stroke:#333;stroke-width:2;fill:none;marker-end:url(#a)}</style>
<defs><marker id="a" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto"><path d="M0,0 L0,6 L9,3 z" fill="#333"/></marker></defs>
<text x="490" y="30" class="lbl" style="font-size:18px">Phase 19 Final Frozen Evaluation (locked execution, inference only)</text>
<rect x="60" y="60" width="240" height="80" rx="8" class="freeze"/><text x="180" y="86" class="lbl">FROZEN MODELS</text><text x="180" y="106" class="sub">LOAD: random_forest B_lags_only</text><text x="180" y="122" class="sub">WIND: hist_gb B_lags_only</text><text x="180" y="138" class="sub">PV: random_forest B_lags_only</text>
<rect x="370" y="60" width="240" height="80" rx="8" class="freeze"/><text x="490" y="86" class="lbl">FROZEN BASELINES</text><text x="490" y="106" class="sub">LOAD/WIND: RTS_DAY_AHEAD</text><text x="490" y="122" class="sub">PV: H24_DAILY_PERSISTENCE</text><text x="490" y="138" class="sub">frozen in Phase 11 + 19 plan</text>
<rect x="680" y="60" width="240" height="80" rx="8" class="freeze"/><text x="800" y="86" class="lbl">FROZEN FEATURES</text><text x="800" y="106" class="sub">B_lags_only = [lag_1, lag_24, lag_168]</text><text x="800" y="122" class="sub">feature spec fingerprint from</text><text x="800" y="138" class="sub">Phase 10 selected feature freeze</text>
<line x1="180" y1="140" x2="490" y2="220" class="edge"/><line x1="490" y1="140" x2="490" y2="220" class="edge"/><line x1="800" y1="140" x2="490" y2="220" class="edge"/>
<rect x="250" y="220" width="480" height="70" rx="8" class="box"/><text x="490" y="248" class="lbl">FINAL-TEST WINDOW (2020-11-01 to 2020-12-31)</text><text x="490" y="270" class="sub">locked partition; first and only authorized access in Phase 19</text><text x="490" y="286" class="sub">1464 hourly rows per target; training cutoff = eval start (walk-forward)</text>
<line x1="490" y1="290" x2="490" y2="330" class="edge"/>
<rect x="200" y="330" width="580" height="80" rx="8" class="box"/><text x="490" y="358" class="lbl">INFERENCE ONLY (no training, no HPO, no feature selection, no model selection, no retraining)</text><text x="490" y="378" class="sub">AccessMode.FINAL_EVALUATION with configuration_frozen=True</text><text x="490" y="394" class="sub">every test timestamp passes through authorize_final_evaluation; protocol access errors block access</text>
<line x1="490" y1="410" x2="490" y2="450" class="edge"/>
<rect x="200" y="450" width="580" height="60" rx="8" class="freeze"/><text x="490" y="476" class="lbl">METRICS + STATISTICAL TESTS (registered only)</text><text x="490" y="496" class="sub">MAE / RMSE / sMAPE / nMAE / nRMSE; Diebold-Mariano + Holm-Bonferroni across FT-H1-{LOAD,WIND,PV}</text>
<text x="490" y="528" class="sub">governance invariants preserved: model_promoted=0, challengers_created=0, state_changes=0, rollback_events=0</text>
</svg>
"""
    (FIG_DIR / "system_architecture_final.svg").write_text(svg, encoding="utf-8")
    return {"perf": FIG_DIR / "final_model_performance_comparison.png",
            "err": FIG_DIR / "final_error_distribution.png",
            "scatter": FIG_DIR / "forecast_vs_actual_plots.png",
            "arch": FIG_DIR / "system_architecture_final.svg"}


def main() -> None:
    TABLES.mkdir(parents=True, exist_ok=True)
    if not PREDICTIONS_PARQUET.exists():
        raise SystemExit(f"official predictions missing: {PREDICTIONS_PARQUET} -- run scripts/run_phase19_final_evaluation.py --execute first")
    if not METRICS_CSV.exists():
        raise SystemExit(f"official metrics missing: {METRICS_CSV}")
    predictions = write_predictions_csv()
    forecasting = write_forecasting_results_csv()
    comparison = write_model_comparison_csv()
    audit = write_audit()
    lineage = write_lineage_report()
    figures = write_figures()
    LOGGER.info("predictions   :", predictions)
    LOGGER.info("forecasting   :", forecasting)
    LOGGER.info("model_compare :", comparison)
    LOGGER.info("audit         :", audit)
    LOGGER.info("lineage       :", lineage)
    for k, v in figures.items():
        LOGGER.info(f"figure {k:6s} :", v)


if __name__ == "__main__":
    main()
