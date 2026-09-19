#!/usr/bin/env python3
"""Multi-Horizon Forecasting Experiment (H1, H6, H12, H24).

Evaluates forecasting models across short, medium, and day-ahead horizons:
  - Horizons: H1, H6, H12, H24
  - Targets: LOAD, WIND, PV
  - Models: Persistence, Seasonal-Naive, Ridge, Random Forest, HistGradientBoosting, MLP
  - Evaluation: Strictly chronological train (Jan-Oct 2020) and test (Nov-Dec 2020).
  - Metrics: MAE, RMSE, sMAPE, nMAE, nRMSE, baseline comparison.
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import math
import sys
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
import torch
from torch import nn

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from smartgrid_mlops.experimental_design.metrics import mae, rmse, smape, nmae, nrmse
from smartgrid_mlops.experimental_design.schemas import TEST_START, DATA_END_EXCLUSIVE
from smartgrid_mlops.features.pipeline import build_features

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stderr,
)
LOGGER = logging.getLogger("multi_horizon")

HORIZONS = (1, 6, 12, 24)
TARGETS = ("load", "wind", "pv")
SEED = 42


def get_feature_data(target: str, horizon: int):
    feat_path = ROOT / f"data/processed/features/{target}/h{horizon}/combined_v1.parquet"
    if not feat_path.exists():
        LOGGER.info("Building features for %s H%d...", target, horizon)
        build_features(target, horizon)
    table = pq.read_table(feat_path)
    df_dict = table.to_pydict()
    return df_dict


def split_data(df_dict: dict):
    n = len(df_dict["target_timestamp"])
    feature_cols = [c for c in df_dict.keys() if c not in ("forecast_origin", "target_timestamp", "feature_set_version", "target")]
    
    train_indices = []
    test_indices = []
    
    for i in range(n):
        ts = df_dict["target_timestamp"][i]
        if ts < TEST_START:
            train_indices.append(i)
        elif TEST_START <= ts < DATA_END_EXCLUSIVE:
            test_indices.append(i)
            
    X = np.column_stack([df_dict[c] for c in feature_cols])
    y = np.array(df_dict["target"], dtype=float)
    timestamps = [df_dict["target_timestamp"][i] for i in test_indices]
    
    X_train, y_train = X[train_indices], y[train_indices]
    X_test, y_test = X[test_indices], y[test_indices]
    
    return X_train, y_train, X_test, y_test, timestamps, feature_cols


def run_experiment():
    results = []
    predictions_out = {}

    for target in TARGETS:
        for horizon in HORIZONS:
            LOGGER.info("Running evaluation for target=%s horizon=H%d", target, horizon)
            data = get_feature_data(target, horizon)
            X_train, y_train, X_test, y_test, timestamps, feat_cols = split_data(data)

            # Baselines
            # 1. Persistence baseline: predict last observed value at origin (lag_1 for H1, lag_24 for H24)
            lag_col_idx = feat_cols.index("lag_1") if "lag_1" in feat_cols else 0
            y_pred_persist = X_test[:, lag_col_idx]
            
            # 2. Seasonal Naive: lag_24 (daily cycle persistence)
            lag24_idx = feat_cols.index("lag_24") if "lag_24" in feat_cols else lag_col_idx
            y_pred_snaive = X_test[:, lag24_idx]

            persist_mae = mae(y_test, y_pred_persist)
            snaive_mae = mae(y_test, y_pred_snaive)
            benchmark_mae = min(persist_mae, snaive_mae)
            benchmark_name = "PERSISTENCE" if persist_mae <= snaive_mae else "SEASONAL_NAIVE"

            results.append({
                "Target": target,
                "Horizon": f"H{horizon}",
                "Model": "persistence",
                "MAE": round(persist_mae, 4),
                "RMSE": round(rmse(y_test, y_pred_persist), 4),
                "sMAPE": round(smape(y_test, y_pred_persist), 4),
                "nMAE": round(nmae(y_test, y_pred_persist), 4),
                "nRMSE": round(nrmse(y_test, y_pred_persist), 4),
                "Benchmark_MAE": round(benchmark_mae, 4),
                "Relative_Diff_Pct": 0.0,
                "Status": "BASELINE",
            })

            results.append({
                "Target": target,
                "Horizon": f"H{horizon}",
                "Model": "seasonal_naive",
                "MAE": round(snaive_mae, 4),
                "RMSE": round(rmse(y_test, y_pred_snaive), 4),
                "sMAPE": round(smape(y_test, y_pred_snaive), 4),
                "nMAE": round(nmae(y_test, y_pred_snaive), 4),
                "nRMSE": round(nrmse(y_test, y_pred_snaive), 4),
                "Benchmark_MAE": round(benchmark_mae, 4),
                "Relative_Diff_Pct": round(100.0 * (snaive_mae - benchmark_mae) / benchmark_mae, 2),
                "Status": "BASELINE",
            })

            # Machine Learning Models
            # 3. Ridge Regression
            ridge = Pipeline([("scaler", StandardScaler()), ("ridge", Ridge(alpha=100.0, random_state=SEED))])
            ridge.fit(X_train, y_train)
            y_pred_ridge = ridge.predict(X_test)
            r_mae = mae(y_test, y_pred_ridge)
            results.append({
                "Target": target,
                "Horizon": f"H{horizon}",
                "Model": "ridge",
                "MAE": round(r_mae, 4),
                "RMSE": round(rmse(y_test, y_pred_ridge), 4),
                "sMAPE": round(smape(y_test, y_pred_ridge), 4),
                "nMAE": round(nmae(y_test, y_pred_ridge), 4),
                "nRMSE": round(nrmse(y_test, y_pred_ridge), 4),
                "Benchmark_MAE": round(benchmark_mae, 4),
                "Relative_Diff_Pct": round(100.0 * (r_mae - benchmark_mae) / benchmark_mae, 2),
                "Status": "BETTER" if r_mae < benchmark_mae else "WORSE",
            })

            # 4. HistGradientBoosting
            hgb = HistGradientBoostingRegressor(max_iter=100, max_depth=6, random_state=SEED)
            hgb.fit(X_train, y_train)
            y_pred_hgb = hgb.predict(X_test)
            hgb_mae = mae(y_test, y_pred_hgb)
            results.append({
                "Target": target,
                "Horizon": f"H{horizon}",
                "Model": "hist_gradient_boosting",
                "MAE": round(hgb_mae, 4),
                "RMSE": round(rmse(y_test, y_pred_hgb), 4),
                "sMAPE": round(smape(y_test, y_pred_hgb), 4),
                "nMAE": round(nmae(y_test, y_pred_hgb), 4),
                "nRMSE": round(nrmse(y_test, y_pred_hgb), 4),
                "Benchmark_MAE": round(benchmark_mae, 4),
                "Relative_Diff_Pct": round(100.0 * (hgb_mae - benchmark_mae) / benchmark_mae, 2),
                "Status": "BETTER" if hgb_mae < benchmark_mae else "WORSE",
            })

            # 5. Random Forest
            rf = RandomForestRegressor(n_estimators=50, max_depth=12, random_state=SEED, n_jobs=-1)
            rf.fit(X_train, y_train)
            y_pred_rf = rf.predict(X_test)
            rf_mae = mae(y_test, y_pred_rf)
            results.append({
                "Target": target,
                "Horizon": f"H{horizon}",
                "Model": "random_forest",
                "MAE": round(rf_mae, 4),
                "RMSE": round(rmse(y_test, y_pred_rf), 4),
                "sMAPE": round(smape(y_test, y_pred_rf), 4),
                "nMAE": round(nmae(y_test, y_pred_rf), 4),
                "nRMSE": round(nrmse(y_test, y_pred_rf), 4),
                "Benchmark_MAE": round(benchmark_mae, 4),
                "Relative_Diff_Pct": round(100.0 * (rf_mae - benchmark_mae) / benchmark_mae, 2),
                "Status": "BETTER" if rf_mae < benchmark_mae else "WORSE",
            })

            # 6. PyTorch MLP
            scaler = StandardScaler()
            X_tr_sc = scaler.fit_transform(X_train)
            X_te_sc = scaler.transform(X_test)
            torch.manual_seed(SEED)
            net = nn.Sequential(
                nn.Linear(X_train.shape[1], 64),
                nn.ReLU(),
                nn.Linear(64, 32),
                nn.ReLU(),
                nn.Linear(32, 1)
            )
            optimizer = torch.optim.Adam(net.parameters(), lr=0.005)
            criterion = nn.L1Loss()
            
            # Fast batch training (10 epochs)
            X_tensor = torch.tensor(X_tr_sc, dtype=torch.float32)
            y_tensor = torch.tensor(y_train, dtype=torch.float32).unsqueeze(-1)
            dataset = torch.utils.data.TensorDataset(X_tensor, y_tensor)
            loader = torch.utils.data.DataLoader(dataset, batch_size=256, shuffle=False)
            
            net.train()
            for _ in range(10):
                for bx, by in loader:
                    optimizer.zero_grad()
                    pred = net(bx)
                    loss = criterion(pred, by)
                    loss.backward()
                    optimizer.step()
                    
            net.eval()
            with torch.no_grad():
                y_pred_mlp = net(torch.tensor(X_te_sc, dtype=torch.float32)).squeeze(-1).numpy()
            mlp_mae = mae(y_test, y_pred_mlp)
            results.append({
                "Target": target,
                "Horizon": f"H{horizon}",
                "Model": "mlp",
                "MAE": round(mlp_mae, 4),
                "RMSE": round(rmse(y_test, y_pred_mlp), 4),
                "sMAPE": round(smape(y_test, y_pred_mlp), 4),
                "nMAE": round(nmae(y_test, y_pred_mlp), 4),
                "nRMSE": round(nrmse(y_test, y_pred_mlp), 4),
                "Benchmark_MAE": round(benchmark_mae, 4),
                "Relative_Diff_Pct": round(100.0 * (mlp_mae - benchmark_mae) / benchmark_mae, 2),
                "Status": "BETTER" if mlp_mae < benchmark_mae else "WORSE",
            })

            predictions_out[f"{target}_{horizon}"] = {
                "timestamps": [str(t) for t in timestamps[:200]],
                "actual": [float(v) for v in y_test[:200]],
                "rf_pred": [float(v) for v in y_pred_rf[:200]],
                "hgb_pred": [float(v) for v in y_pred_hgb[:200]],
            }

    # Save research table
    out_table = ROOT / "artifacts/research_tables/multi_horizon_comparison.csv"
    out_table.parent.mkdir(parents=True, exist_ok=True)
    with out_table.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)
    LOGGER.info("Saved multi-horizon results to %s", out_table)

    # Generate publication figures
    generate_figures(results)


def generate_figures(results: list[dict]):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig_dir = ROOT / "artifacts/research_figures"
    fig_dir.mkdir(parents=True, exist_ok=True)

    # Plot 1: MAE across horizons for each target
    targets = ["load", "wind", "pv"]
    models = ["persistence", "ridge", "hist_gradient_boosting", "random_forest", "mlp"]
    horizons = ["H1", "H6", "H12", "H24"]

    fig, axes = plt.subplots(1, 3, figsize=(15, 5), sharex=True)
    colors = {"persistence": "#888888", "ridge": "#2ca02c", "hist_gradient_boosting": "#1f77b4", "random_forest": "#ff7f0e", "mlp": "#9467bd"}

    for idx, target in enumerate(targets):
        ax = axes[idx]
        for model in models:
            maes = []
            for h in horizons:
                match = next((r for r in results if r["Target"] == target and r["Horizon"] == h and r["Model"] == model), None)
                if match:
                    maes.append(match["MAE"])
                else:
                    maes.append(np.nan)
            ax.plot(horizons, maes, marker="o", linewidth=2, label=model, color=colors.get(model))
        ax.set_title(f"Target: {target.upper()}", fontsize=13, fontweight="bold")
        ax.set_xlabel("Forecast Horizon", fontsize=11)
        ax.set_ylabel("MAE (MW)", fontsize=11)
        ax.grid(True, linestyle="--", alpha=0.6)
        if idx == 0:
            ax.legend(frameon=True, fontsize=9)

    plt.suptitle("Multi-Horizon Forecasting Performance (H1 to H24)", fontsize=15, fontweight="bold", y=1.02)
    plt.tight_layout()
    plt.savefig(fig_dir / "multi_horizon_performance.png", dpi=300, bbox_inches="tight")
    plt.savefig(fig_dir / "multi_horizon_performance.svg", bbox_inches="tight")
    plt.close()
    LOGGER.info("Generated multi-horizon performance figures.")


if __name__ == "__main__":
    run_experiment()
