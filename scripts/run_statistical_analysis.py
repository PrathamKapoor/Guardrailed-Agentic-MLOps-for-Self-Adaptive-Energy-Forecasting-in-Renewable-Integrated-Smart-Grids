#!/usr/bin/env python3
"""Statistical Significance Analysis for Time-Series Forecasts.

Implements rigorous, autocorrelation-aware statistical evaluation:
  1. 24-Hour Block Bootstrap 95% Confidence Intervals for MAE and RMSE
     (avoids invalid i.i.d. assumption on autocorrelated hourly time series).
  2. Diebold-Mariano Test (with Harvey-Leybourne-Newbold small-sample correction)
     for comparing paired time-series forecast accuracy.
  3. Wilcoxon Signed-Rank Test for non-parametric paired error comparisons.
  4. Effect Sizes (Cohen's d on loss differentials).
"""
from __future__ import annotations

import csv
import json
import logging
import math
import sys
from pathlib import Path

import numpy as np
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from smartgrid_mlops.experimental_design.metrics import mae, rmse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stderr,
)
LOGGER = logging.getLogger("statistical_analysis")

SEED = 42


def diebold_mariano_test(e1: np.ndarray, e2: np.ndarray, horizon: int = 24) -> tuple[float, float]:
    """Diebold-Mariano test with Harvey-Leybourne-Newbold correction for h-step ahead forecasts."""
    # Loss differential (using absolute error loss)
    d = np.abs(e1) - np.abs(e2)
    n = len(d)
    mean_d = np.mean(d)
    
    # Autocovariance up to lag h-1
    gamma_0 = np.var(d, ddof=0)
    gamma_sum = 0.0
    for k in range(1, horizon):
        gamma_k = np.cov(d[:-k], d[k:])[0, 1] if k < n else 0.0
        # Bartlett weight
        w = 1.0 - (k / horizon)
        gamma_sum += 2.0 * w * gamma_k
        
    lr_var = max(1e-12, gamma_0 + gamma_sum)
    dm_stat = mean_d / np.sqrt(lr_var / n)
    
    # HLN small-sample correction
    hln_factor = np.sqrt((n + 1 - 2 * horizon + horizon * (horizon - 1) / n) / n)
    dm_stat_corrected = dm_stat * hln_factor
    
    # Two-tailed p-value from Student's t distribution with n-1 degrees of freedom
    p_value = 2.0 * (1.0 - stats.t.cdf(np.abs(dm_stat_corrected), df=n - 1))
    return float(dm_stat_corrected), float(p_value)


def block_bootstrap_ci(actual: np.ndarray, pred: np.ndarray, block_size: int = 24, n_boot: int = 1000) -> dict:
    """Block bootstrap 95% confidence intervals for MAE and RMSE."""
    rng = np.random.RandomState(SEED)
    n = len(actual)
    n_blocks = int(np.ceil(n / block_size))
    
    mae_dist = []
    rmse_dist = []
    
    for _ in range(n_boot):
        # Sample starting indices of blocks
        starts = rng.randint(0, n - block_size + 1, size=n_blocks)
        indices = np.concatenate([np.arange(s, s + block_size) for s in starts])[:n]
        
        act_b = actual[indices]
        prd_b = pred[indices]
        mae_dist.append(mae(act_b, prd_b))
        rmse_dist.append(rmse(act_b, prd_b))
        
    return {
        "mae_ci_lower": float(np.percentile(mae_dist, 2.5)),
        "mae_ci_upper": float(np.percentile(mae_dist, 97.5)),
        "rmse_ci_lower": float(np.percentile(rmse_dist, 2.5)),
        "rmse_ci_upper": float(np.percentile(rmse_dist, 97.5)),
        "mae_std_err": float(np.std(mae_dist)),
    }


def run_analysis():
    pred_path = ROOT / "artifacts/research_tables/final_predictions.csv"
    if not pred_path.exists():
        raise FileNotFoundError(f"Missing {pred_path}")
        
    rows = list(csv.DictReader(pred_path.open(encoding="utf-8")))
    
    # Group by (target, model)
    groups: dict[tuple[str, str], dict[str, list[float]]] = {}
    for r in rows:
        key = (r["target"], r["model"])
        if key not in groups:
            groups[key] = {"actual": [], "prediction": []}
        groups[key]["actual"].append(float(r["actual"]))
        groups[key]["prediction"].append(float(r["prediction"]))

    comparisons = [
        # (target, candidate_model, baseline_model)
        ("load", "random_forest", "RTS_DAY_AHEAD"),
        ("load", "mlp", "RTS_DAY_AHEAD"),
        ("wind", "hist_gradient_boosting", "RTS_DAY_AHEAD"),
        ("wind", "mlp", "RTS_DAY_AHEAD"),
        ("pv", "random_forest", "H24_DAILY_PERSISTENCE"),
        ("pv", "mlp", "H24_DAILY_PERSISTENCE"),
    ]

    results = []
    plot_data = []

    for target, cand_name, base_name in comparisons:
        LOGGER.info("Computing statistics for %s: %s vs %s", target, cand_name, base_name)
        cand = groups[(target, cand_name)]
        base = groups[(target, base_name)]
        
        act = np.array(cand["actual"])
        pred_cand = np.array(cand["prediction"])
        pred_base = np.array(base["prediction"])
        
        err_cand = act - pred_cand
        err_base = act - pred_base
        
        cand_mae = mae(act, pred_cand)
        base_mae = mae(act, pred_base)
        
        # Block bootstrap CIs
        cand_ci = block_bootstrap_ci(act, pred_cand)
        base_ci = block_bootstrap_ci(act, pred_base)
        
        # Diebold-Mariano Test
        dm_stat, dm_p = diebold_mariano_test(err_cand, err_base, horizon=24)
        
        # Wilcoxon Signed-Rank Test on absolute errors
        diff_abs = np.abs(err_cand) - np.abs(err_base)
        w_stat, w_p = stats.wilcoxon(diff_abs, zero_method="pratt")
        
        # Cohen's d effect size on loss differential
        cohens_d = float(np.mean(diff_abs) / (np.std(diff_abs, ddof=1) + 1e-12))
        
        # Interpretation:
        # Negative mean diff means candidate has lower error (better).
        # Positive mean diff means baseline has lower error (candidate is worse).
        if dm_p < 0.05:
            sig_result = "STATISTICALLY_SIGNIFICANT_BETTER" if cand_mae < base_mae else "STATISTICALLY_SIGNIFICANT_WORSE"
        else:
            sig_result = "NO_SIGNIFICANT_DIFFERENCE"

        results.append({
            "Target": target,
            "Candidate_Model": cand_name,
            "Baseline_Model": base_name,
            "Candidate_MAE": round(cand_mae, 4),
            "Candidate_MAE_95_CI": f"[{cand_ci['mae_ci_lower']:.2f}, {cand_ci['mae_ci_upper']:.2f}]",
            "Baseline_MAE": round(base_mae, 4),
            "Baseline_MAE_95_CI": f"[{base_ci['mae_ci_lower']:.2f}, {base_ci['mae_ci_upper']:.2f}]",
            "Diebold_Mariano_Stat": round(dm_stat, 4),
            "Diebold_Mariano_P_Value": f"{dm_p:.4e}",
            "Wilcoxon_P_Value": f"{w_p:.4e}",
            "Cohens_d": round(cohens_d, 4),
            "Significance_Outcome": sig_result,
        })
        
        plot_data.append({
            "target": target,
            "candidate": cand_name,
            "baseline": base_name,
            "cand_mae": cand_mae,
            "cand_ci": cand_ci,
            "base_mae": base_mae,
            "base_ci": base_ci,
            "diff_abs": diff_abs,
        })

    out_table = ROOT / "artifacts/research_tables/statistical_significance_results.csv"
    out_table.parent.mkdir(parents=True, exist_ok=True)
    with out_table.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        w.writeheader()
        w.writerows(results)
    LOGGER.info("Saved statistical significance results to %s", out_table)

    generate_figures(plot_data)


def generate_figures(plot_data: list[dict]):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig_dir = ROOT / "artifacts/research_figures"
    fig_dir.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    for idx, d in enumerate([plot_data[0], plot_data[2], plot_data[4]]):
        ax = axes[idx]
        target = d["target"].upper()
        
        models = [d["candidate"], d["baseline"]]
        maes = [d["cand_mae"], d["base_mae"]]
        yerr = [
            [d["cand_mae"] - d["cand_ci"]["mae_ci_lower"], d["base_mae"] - d["base_ci"]["mae_ci_lower"]],
            [d["cand_ci"]["mae_ci_upper"] - d["cand_mae"], d["base_ci"]["mae_ci_upper"] - d["base_mae"]],
        ]
        
        bars = ax.bar(models, maes, yerr=yerr, capsize=6, color=["#1f77b4", "#888888"], width=0.5)
        ax.set_title(f"{target}: Model vs Baseline (95% CI)", fontsize=11, fontweight="bold")
        ax.set_ylabel("MAE (MW)", fontsize=10)
        ax.grid(True, linestyle="--", alpha=0.5)
        
        # Add labels
        for bar in bars:
            h = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., h/2, f"{h:.1f}", ha="center", va="center", color="white", fontweight="bold")

    plt.suptitle("Forecast Accuracy with 24-Hour Block Bootstrap 95% Confidence Intervals", fontsize=13, fontweight="bold", y=1.02)
    plt.tight_layout()
    plt.savefig(fig_dir / "error_distributions_and_confidence_intervals.png", dpi=300, bbox_inches="tight")
    plt.savefig(fig_dir / "error_distributions_and_confidence_intervals.svg", bbox_inches="tight")
    plt.close()
    LOGGER.info("Generated statistical figures.")


if __name__ == "__main__":
    run_analysis()
