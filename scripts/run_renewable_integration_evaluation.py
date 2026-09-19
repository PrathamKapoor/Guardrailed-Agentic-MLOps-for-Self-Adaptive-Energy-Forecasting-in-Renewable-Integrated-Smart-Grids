#!/usr/bin/env python3
"""Renewable Energy Integration Evaluation.

Evaluates smart-grid forecasting from a grid-integration perspective:
  - Total renewable generation: WIND + PV
  - Net load: LOAD - (WIND + PV)
  - Renewable-to-load matching ratio: (WIND + PV) / LOAD
  - Surplus renewable conditions: (WIND + PV) > LOAD
  - Deficit conditions: (WIND + PV) < LOAD
  - Net load forecast error (MAE, RMSE)
  - Surplus/deficit classification metrics (Precision, Recall, F1)
"""
from __future__ import annotations

import csv
import json
import logging
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from smartgrid_mlops.experimental_design.metrics import mae, rmse, smape

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stderr,
)
LOGGER = logging.getLogger("renewable_integration")


def load_final_predictions() -> dict:
    pred_path = ROOT / "artifacts/research_tables/final_predictions.csv"
    if not pred_path.exists():
        raise FileNotFoundError(f"Missing {pred_path}")
    
    rows = list(csv.DictReader(pred_path.open(encoding="utf-8")))
    
    # Organize by (target, model) -> {timestamp: (actual, prediction)}
    data = {}
    for r in rows:
        key = (r["target"], r["model"])
        if key not in data:
            data[key] = {}
        data[key][r["timestamp"]] = (float(r["actual"]), float(r["prediction"]))
    return data


def run_evaluation():
    data = load_final_predictions()
    
    # Primary frozen models:
    # LOAD: random_forest
    # WIND: hist_gradient_boosting
    # PV: random_forest
    # Baselines:
    # LOAD: RTS_DAY_AHEAD
    # WIND: RTS_DAY_AHEAD
    # PV: H24_DAILY_PERSISTENCE
    
    configs = [
        {
            "name": "FROZEN_ML_MODELS",
            "load_model": "random_forest",
            "wind_model": "hist_gradient_boosting",
            "pv_model": "random_forest"
        },
        {
            "name": "EXTERNAL_BASELINES",
            "load_model": "RTS_DAY_AHEAD",
            "wind_model": "RTS_DAY_AHEAD",
            "pv_model": "H24_DAILY_PERSISTENCE"
        },
        {
            "name": "NEURAL_MLP_MODELS",
            "load_model": "mlp",
            "wind_model": "mlp",
            "pv_model": "mlp"
        }
    ]
    
    results = []
    series_records = {}

    for cfg in configs:
        name = cfg["name"]
        load_data = data[("load", cfg["load_model"])]
        wind_data = data[("wind", cfg["wind_model"])]
        pv_data = data[("pv", cfg["pv_model"])]
        
        common_timestamps = sorted(set(load_data.keys()) & set(wind_data.keys()) & set(pv_data.keys()))
        n = len(common_timestamps)
        
        actual_load = np.array([load_data[t][0] for t in common_timestamps])
        pred_load = np.array([load_data[t][1] for t in common_timestamps])
        
        actual_wind = np.array([wind_data[t][0] for t in common_timestamps])
        pred_wind = np.array([wind_data[t][1] for t in common_timestamps])
        
        actual_pv = np.array([pv_data[t][0] for t in common_timestamps])
        pred_pv = np.array([pv_data[t][1] for t in common_timestamps])
        
        actual_renewable = actual_wind + actual_pv
        pred_renewable = pred_wind + pred_pv
        
        actual_net_load = actual_load - actual_renewable
        pred_net_load = pred_load - pred_renewable
        
        # Renewable-to-load matching ratio
        actual_matching = actual_renewable / np.maximum(actual_load, 1e-6)
        pred_matching = pred_renewable / np.maximum(pred_load, 1e-6)
        
        # Surplus conditions: renewable > load
        actual_surplus = actual_renewable > actual_load
        pred_surplus = pred_renewable > pred_load
        
        tp = np.sum(actual_surplus & pred_surplus)
        fp = np.sum((~actual_surplus) & pred_surplus)
        fn = np.sum(actual_surplus & (~pred_surplus))
        tn = np.sum((~actual_surplus) & (~pred_surplus))
        
        precision = float(tp / (tp + fp)) if (tp + fp) > 0 else 1.0
        recall = float(tp / (tp + fn)) if (tp + fn) > 0 else 1.0
        f1 = float(2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
        accuracy = float((tp + tn) / n)
        
        # Magnitude errors
        net_load_mae = mae(actual_net_load, pred_net_load)
        net_load_rmse = rmse(actual_net_load, pred_net_load)
        renewable_mae = mae(actual_renewable, pred_renewable)
        renewable_rmse = rmse(actual_renewable, pred_renewable)
        matching_ratio_mae = float(np.mean(np.abs(actual_matching - pred_matching)))
        
        # Surplus magnitude error
        actual_surplus_mag = np.maximum(0, actual_renewable - actual_load)
        pred_surplus_mag = np.maximum(0, pred_renewable - pred_load)
        surplus_mae = float(np.mean(np.abs(actual_surplus_mag - pred_surplus_mag)))
        
        results.append({
            "Configuration": name,
            "Total_Hours": n,
            "Net_Load_MAE": round(net_load_mae, 4),
            "Net_Load_RMSE": round(net_load_rmse, 4),
            "Total_Renewable_MAE": round(renewable_mae, 4),
            "Total_Renewable_RMSE": round(renewable_rmse, 4),
            "Matching_Ratio_MAE": round(matching_ratio_mae, 4),
            "Surplus_Hours_Actual": int(np.sum(actual_surplus)),
            "Surplus_Hours_Predicted": int(np.sum(pred_surplus)),
            "Surplus_Classification_Accuracy": round(accuracy, 4),
            "Surplus_Precision": round(precision, 4),
            "Surplus_Recall": round(recall, 4),
            "Surplus_F1": round(f1, 4),
            "Surplus_Magnitude_MAE": round(surplus_mae, 4),
        })
        
        if name == "FROZEN_ML_MODELS":
            series_records = {
                "timestamps": common_timestamps,
                "actual_load": actual_load,
                "pred_load": pred_load,
                "actual_net_load": actual_net_load,
                "pred_net_load": pred_net_load,
                "actual_renewable": actual_renewable,
                "pred_renewable": pred_renewable,
                "actual_matching": actual_matching,
                "pred_matching": pred_matching,
            }

    out_table = ROOT / "artifacts/research_tables/renewable_integration_metrics.csv"
    out_table.parent.mkdir(parents=True, exist_ok=True)
    with out_table.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)
    LOGGER.info("Saved renewable integration metrics to %s", out_table)

    generate_figures(series_records, results)


def generate_figures(series: dict, results: list[dict]):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig_dir = ROOT / "artifacts/research_figures"
    fig_dir.mkdir(parents=True, exist_ok=True)

    # 4-panel renewable integration figure
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # Panel 1: Net Load Actual vs Predicted over a 168h week
    ax1 = axes[0, 0]
    sample_slice = slice(0, 168)
    hours = np.arange(168)
    ax1.plot(hours, series["actual_net_load"][sample_slice], label="Actual Net Load", color="#1f77b4", linewidth=2)
    ax1.plot(hours, series["pred_net_load"][sample_slice], label="Predicted Net Load (Frozen ML)", color="#ff7f0e", linestyle="--", linewidth=2)
    ax1.set_title("(a) 7-Day Net Load Profile (LOAD - WIND - PV)", fontsize=11, fontweight="bold")
    ax1.set_xlabel("Hour of Week", fontsize=10)
    ax1.set_ylabel("Power (MW)", fontsize=10)
    ax1.grid(True, linestyle="--", alpha=0.5)
    ax1.legend(frameon=True, fontsize=9)

    # Panel 2: Total Renewable Actual vs Predicted
    ax2 = axes[0, 1]
    ax2.plot(hours, series["actual_renewable"][sample_slice], label="Actual Renewables (WIND + PV)", color="#2ca02c", linewidth=2)
    ax2.plot(hours, series["pred_renewable"][sample_slice], label="Predicted Renewables", color="#d62728", linestyle="--", linewidth=2)
    ax2.set_title("(b) 7-Day Renewable Generation Profile", fontsize=11, fontweight="bold")
    ax2.set_xlabel("Hour of Week", fontsize=10)
    ax2.set_ylabel("Generation (MW)", fontsize=10)
    ax2.grid(True, linestyle="--", alpha=0.5)
    ax2.legend(frameon=True, fontsize=9)

    # Panel 3: Matching Ratio Distribution
    ax3 = axes[1, 0]
    ax3.hist(series["actual_matching"], bins=30, alpha=0.6, label="Actual Matching Ratio", color="#2ca02c", density=True)
    ax3.hist(series["pred_matching"], bins=30, alpha=0.6, label="Predicted Matching Ratio", color="#1f77b4", density=True)
    ax3.set_title("(c) Renewable-to-Load Matching Ratio Distribution", fontsize=11, fontweight="bold")
    ax3.set_xlabel("Matching Ratio ((WIND + PV) / LOAD)", fontsize=10)
    ax3.set_ylabel("Density", fontsize=10)
    ax3.grid(True, linestyle="--", alpha=0.5)
    ax3.legend(frameon=True, fontsize=9)

    # Panel 4: Metric Comparison Bar Chart across Configurations
    ax4 = axes[1, 1]
    configs = [r["Configuration"].replace("_", "\n") for r in results]
    net_mae = [r["Net_Load_MAE"] for r in results]
    ren_mae = [r["Total_Renewable_MAE"] for r in results]
    x = np.arange(len(configs))
    width = 0.35
    ax4.bar(x - width/2, net_mae, width, label="Net Load MAE (MW)", color="#1f77b4")
    ax4.bar(x + width/2, ren_mae, width, label="Renewables MAE (MW)", color="#2ca02c")
    ax4.set_title("(d) Grid Integration MAE Comparison", fontsize=11, fontweight="bold")
    ax4.set_xticks(x)
    ax4.set_xticklabels(configs, fontsize=9)
    ax4.set_ylabel("MAE (MW)", fontsize=10)
    ax4.grid(True, linestyle="--", alpha=0.5)
    ax4.legend(frameon=True, fontsize=9)

    plt.suptitle("Renewable Energy Integration and Net Load Analytics (RTS-GMLC 2020 Test Window)", fontsize=14, fontweight="bold", y=0.99)
    plt.tight_layout()
    plt.savefig(fig_dir / "renewable_integration_analysis.png", dpi=300, bbox_inches="tight")
    plt.savefig(fig_dir / "renewable_integration_analysis.svg", bbox_inches="tight")
    plt.close()
    LOGGER.info("Generated renewable integration figures.")


if __name__ == "__main__":
    run_evaluation()
