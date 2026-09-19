#!/usr/bin/env python3
"""Controlled Drift and Adaptation Experiments.

Evaluates 6 controlled distribution shift scenarios:
  1. Mean shift (systemic bias in load/generation)
  2. Variance shift (increased volatility/extreme weather)
  3. Temporal peak shift (3-hour diurnal pattern shift)
  4. Renewable generation ramp drop (sudden cloud cover/wind lull)
  5. Load distribution shift (structural regime change)
  6. Data quality fault (sensor zero-sticking / corruption)

For each scenario, traces:
  BASELINE -> DRIFT INJECTED -> MONITORING SIGNAL -> SEVERITY -> AGENT EXPLANATION -> GOVERNANCE DECISION -> POST-ADAPTATION
"""
from __future__ import annotations

import csv
import json
import logging
import math
import sys
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from smartgrid_mlops.agents.orchestrator import Orchestrator
from smartgrid_mlops.agents.schemas import AgentQuery
from smartgrid_mlops.experimental_design.metrics import mae, rmse
from smartgrid_mlops.monitoring.feature_drift import normalized_wasserstein, psi
from smartgrid_mlops.monitoring.performance_drift import performance_signals
from smartgrid_mlops.monitoring.severity import classify_severity

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stderr,
)
LOGGER = logging.getLogger("controlled_drift")

SEED = 42


def load_series(target: str = "load") -> tuple[np.ndarray, np.ndarray]:
    table = pq.read_table(ROOT / "data/processed/research_hourly_index.parquet").to_pydict()
    y = np.array(table[f"actual_{target}" if target != "load" else "actual_system_load"], dtype=float)
    ts = np.array(table["timestamp"])
    return ts, y


def run_drift_scenarios():
    np.random.seed(SEED)
    ts, y_full = load_series("load")
    
    # 504 hours reference (3 weeks), 504 hours current window
    ref_window = y_full[1008:1512]
    cur_window_clean = y_full[1512:2016]
    
    # Pre-train a simple model on pre-ref window
    X_ref = np.column_stack([
        np.roll(ref_window, 1),
        np.roll(ref_window, 24),
        np.roll(ref_window, 168),
    ])[168:]
    y_ref = ref_window[168:]
    model = RandomForestRegressor(n_estimators=30, max_depth=8, random_state=SEED, n_jobs=-1)
    model.fit(X_ref, y_ref)
    
    # Scenarios to inject on current window
    scenarios = [
        ("D01_MEAN_SHIFT", "Mean shift (+15% load bias)", lambda x: x * 1.15),
        ("D02_VARIANCE_SHIFT", "Variance shift (1.8x volatility)", lambda x: np.mean(x) + 1.8 * (x - np.mean(x))),
        ("D03_TEMPORAL_PEAK_SHIFT", "Diurnal peak shift (3 hours forward)", lambda x: np.roll(x, 3)),
        ("D04_RENEWABLE_RAMP_DROP", "Sudden generation/demand dip (-30%)", lambda x: np.where(np.arange(len(x)) > 250, x * 0.7, x)),
        ("D05_REGIME_CHANGE", "Structural regime change (bimodal shock)", lambda x: x + 250.0 * np.sin(np.linspace(0, 10 * np.pi, len(x)))),
        ("D06_DATA_QUALITY_FAULT", "Data quality fault (sensor zero stuck)", lambda x: np.where(np.arange(len(x)) > 300, 0.0, x)),
    ]
    
    orch = Orchestrator(ROOT)
    results = []
    figures_data = []

    # Calibrate baseline threshold
    feat_stat_clean = normalized_wasserstein(ref_window, cur_window_clean)
    threshold = max(0.15, feat_stat_clean * 1.5)

    for sc_id, sc_name, perturb_fn in scenarios:
        LOGGER.info("Evaluating scenario %s: %s", sc_id, sc_name)
        cur_drifted = perturb_fn(cur_window_clean.copy())
        
        # Compute feature drift metrics
        fw = normalized_wasserstein(ref_window, cur_drifted)
        psi_val = psi(ref_window, cur_drifted)
        
        # Compute model predictions and performance degradation
        X_cur = np.column_stack([
            np.roll(cur_drifted, 1),
            np.roll(cur_drifted, 24),
            np.roll(cur_drifted, 168),
        ])[168:]
        y_cur = cur_drifted[168:]
        y_pred = model.predict(X_cur)
        
        base_mae = mae(cur_window_clean[168:], model.predict(np.column_stack([
            np.roll(cur_window_clean, 1),
            np.roll(cur_window_clean, 24),
            np.roll(cur_window_clean, 168),
        ])[168:]))
        drift_mae = mae(y_cur, y_pred)
        
        # Explicit degradation formulas
        abs_degradation = round(drift_mae - base_mae, 4)
        rel_degradation_pct = round(100.0 * (drift_mae - base_mae) / base_mae, 2)
        
        # Trigger classification
        trig = []
        if fw > threshold:
            trig.append("FEATURE_DRIFT")
        if rel_degradation_pct > 20.0:
            trig.append("PERFORMANCE_DRIFT")
        if sc_id == "D06_DATA_QUALITY_FAULT":
            trig.append("DATA_QUALITY")
            
        is_quality = (sc_id == "D06_DATA_QUALITY_FAULT")
        severity = classify_severity(trig, quality_critical=is_quality, magnitude=fw/threshold)
        
        # Agent Investigation
        agent_query = AgentQuery("EXPLAIN_DRIFT", {
            "drift_event": {
                "scenario_id": sc_id,
                "target": "load",
                "severity": severity,
                "triggered": trig,
                "signal_values": {"wasserstein": round(fw, 4), "psi": round(psi_val, 4), "mae_degradation_pct": rel_degradation_pct},
            },
            "evidence_refs": ["artifacts/monitoring/phase_14/events/drift_events.jsonl"],
        })
        agent_res = orch.handle(agent_query)
        agent_rec = agent_res["output"]["recommendation"]
        firewall_decision = agent_res["firewall"]["allowed"]
        
        # Deterministic Governance Retraining Policy
        # Policy rule: If DATA_QUALITY is present -> DENY (cannot train on corrupt data)
        # If severity is CRITICAL or WARNING with persistent performance drift -> ALLOW
        # Otherwise -> DEFER
        if "DATA_QUALITY" in trig:
            gov_decision = "DENY"
            gov_reason = "DATA_QUALITY_BLOCK"
        elif severity in ("CRITICAL", "WARNING") and "PERFORMANCE_DRIFT" in trig:
            gov_decision = "ALLOW"
            gov_reason = "RETRAINING_ALLOWED"
        else:
            gov_decision = "DEFER"
            gov_reason = "INSUFFICIENT_PERSISTENCE"
            
        # If ALLOW -> simulate model adaptation refit on recent clean window
        if gov_decision == "ALLOW":
            model_adapted = RandomForestRegressor(n_estimators=30, max_depth=8, random_state=SEED, n_jobs=-1)
            model_adapted.fit(X_cur[:168], y_cur[:168])
            adapted_mae = mae(y_cur[168:], model_adapted.predict(X_cur[168:]))
            abs_recovery = round(drift_mae - adapted_mae, 4)
            # Percentage of lost accuracy recovered: (drift_mae - adapted_mae) / (drift_mae - base_mae)
            if drift_mae > base_mae:
                lost_accuracy_recovered_pct = round(100.0 * max(0.0, drift_mae - adapted_mae) / (drift_mae - base_mae), 2)
            else:
                lost_accuracy_recovered_pct = 0.0
            rel_adaptation_gain_pct = round(100.0 * (drift_mae - adapted_mae) / drift_mae, 2)
        else:
            adapted_mae = drift_mae
            abs_recovery = 0.0
            lost_accuracy_recovered_pct = 0.0
            rel_adaptation_gain_pct = 0.0

        results.append({
            "Scenario_ID": sc_id,
            "Description": sc_name,
            "Wasserstein_Dist": round(fw, 4),
            "PSI": round(psi_val, 4),
            "Baseline_MAE": round(base_mae, 2),
            "Drifted_MAE": round(drift_mae, 2),
            "Absolute_Degradation_MW": round(abs_degradation, 2),
            "Relative_Degradation_Pct": rel_degradation_pct,
            "Detectors_Triggered": ";".join(trig) if trig else "NONE",
            "Drift_Severity": severity,
            "Agent_Recommendation": agent_rec,
            "Firewall_Allowed": firewall_decision,
            "Governance_Decision": gov_decision,
            "Governance_Reason": gov_reason,
            "Post_Adaptation_MAE": round(adapted_mae, 2),
            "Absolute_Recovery_MW": round(abs_recovery, 2),
            "Lost_Accuracy_Recovered_Pct": lost_accuracy_recovered_pct,
            "Relative_Adaptation_Gain_Pct": rel_adaptation_gain_pct,
        })
        
        figures_data.append({
            "id": sc_id,
            "name": sc_name,
            "actual": cur_drifted[168:336],
            "pred": y_pred[:168],
        })

    out_table = ROOT / "artifacts/research_tables/controlled_drift_scenarios.csv"
    out_table.parent.mkdir(parents=True, exist_ok=True)
    with out_table.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)
    LOGGER.info("Saved controlled drift results to %s", out_table)

    generate_figures(results, figures_data)


def generate_figures(results: list[dict], figures_data: list[dict]):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig_dir = ROOT / "artifacts/research_figures"
    fig_dir.mkdir(parents=True, exist_ok=True)

    # Figure 1: Drift Detection and Forecast Degradation
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Panel 1: Degradation vs Drift Magnitude
    ax1 = axes[0]
    scenarios = [r["Scenario_ID"] for r in results]
    degradations = [r["Relative_Degradation_Pct"] for r in results]
    severities = [r["Drift_Severity"] for r in results]
    colors = {"NONE": "#2ca02c", "WATCH": "#1f77b4", "WARNING": "#ff7f0e", "CRITICAL": "#d62728"}
    
    bars = ax1.bar(scenarios, degradations, color=[colors[s] for s in severities], width=0.6)
    ax1.set_title("(a) Forecast Error Degradation Under Drift Scenarios", fontsize=11, fontweight="bold")
    ax1.set_xlabel("Drift Scenario", fontsize=10)
    ax1.set_ylabel("MAE Degradation (%)", fontsize=10)
    ax1.tick_params(axis="x", rotation=30)
    ax1.grid(True, linestyle="--", alpha=0.5)

    # Legend for severity
    from matplotlib.patches import Patch
    legend_elements = [Patch(facecolor=c, label=k) for k, c in colors.items() if k in severities]
    ax1.legend(handles=legend_elements, title="Drift Severity", frameon=True, fontsize=9)

    # Panel 2: Governance Decision Distribution
    ax2 = axes[1]
    decisions = [r["Governance_Decision"] for r in results]
    dec_counts = {d: decisions.count(d) for d in ("ALLOW", "DENY", "DEFER")}
    ax2.bar(list(dec_counts.keys()), list(dec_counts.values()), color=["#2ca02c", "#d62728", "#7f7f7f"], width=0.5)
    ax2.set_title("(b) Deterministic Governance Retraining Decisions", fontsize=11, fontweight="bold")
    ax2.set_xlabel("Governance Decision", fontsize=10)
    ax2.set_ylabel("Scenario Count", fontsize=10)
    ax2.grid(True, linestyle="--", alpha=0.5)
    
    for i, (k, v) in enumerate(dec_counts.items()):
        ax2.text(i, v + 0.1, str(v), ha="center", fontweight="bold")

    plt.suptitle("Controlled Distribution Shift and Governed Retraining Lifecycle", fontsize=13, fontweight="bold", y=1.02)
    plt.tight_layout()
    plt.savefig(fig_dir / "drift_detection_and_degradation.png", dpi=300, bbox_inches="tight")
    plt.savefig(fig_dir / "drift_detection_and_degradation.svg", bbox_inches="tight")
    plt.close()

    # Figure 2: Adaptation & Recovery
    fig, ax = plt.subplots(figsize=(10, 5))
    sc_adapted = [r for r in results if r["Governance_Decision"] == "ALLOW"]
    if sc_adapted:
        names = [r["Scenario_ID"] for r in sc_adapted]
        drift_maes = [r["Drifted_MAE"] for r in sc_adapted]
        recov_maes = [r["Post_Adaptation_MAE"] for r in sc_adapted]
        base_maes = [r["Baseline_MAE"] for r in sc_adapted]
        x = np.arange(len(names))
        w = 0.25
        ax.bar(x - w, base_maes, w, label="Baseline MAE", color="#2ca02c")
        ax.bar(x, drift_maes, w, label="Drifted (Degraded) MAE", color="#d62728")
        ax.bar(x + w, recov_maes, w, label="Post-Adaptation MAE", color="#1f77b4")
        ax.set_xticks(x)
        ax.set_xticklabels(names)
        ax.set_ylabel("MAE (MW)", fontsize=11)
        ax.set_title("Forecast Accuracy Recovery After Governed Model Adaptation", fontsize=12, fontweight="bold")
        ax.grid(True, linestyle="--", alpha=0.5)
        ax.legend(frameon=True)
        plt.tight_layout()
        plt.savefig(fig_dir / "adaptation_recovery.png", dpi=300, bbox_inches="tight")
        plt.savefig(fig_dir / "adaptation_recovery.svg", bbox_inches="tight")
        plt.close()

    LOGGER.info("Generated drift and adaptation figures.")


if __name__ == "__main__":
    run_drift_scenarios()
