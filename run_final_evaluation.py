#!/usr/bin/env python3
"""Final-evaluation verification entry point (Phase 19).

The authoritative final evaluation lives in scripts/run_phase19_final_evaluation.py,
which ran ONCE on the sealed test partition after the Phase 19 protocol freeze and
wrote the artifacts verified here. This entry point deliberately does NOT re-run
inference: re-running the sealed evaluation outside the verified pipeline would
risk protocol divergence. Instead it performs a read-only integrity check:

1. Confirm the sealed artifacts exist.
2. Recompute MAE/RMSE/sMAPE/nMAE/nRMSE per (target, model) from the sealed
   predictions CSV.
3. Cross-check the recomputed metrics against the recorded research tables.

Exit code 0 = sealed artifacts verified; non-zero = mismatch or missing artifact.
"""
from __future__ import annotations

import csv
import math
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

# Single source of truth for metric definitions (matches the sealed results).
from smartgrid_mlops.experimental_design.metrics import mae, rmse, smape, nmae, nrmse  # noqa: E402
PREDICTIONS = ROOT / "artifacts" / "research_tables" / "final_predictions.csv"
RESULTS = ROOT / "artifacts" / "research_tables" / "final_forecasting_results.csv"
COMPARISON = ROOT / "artifacts" / "research_tables" / "final_model_comparison.csv"
PROTOCOL = ROOT / "artifacts" / "experimental_design" / "phase_19_final_evaluation_protocol_freeze.yaml"

TOLERANCE = 1e-6


def main() -> int:
    print("Final-evaluation verification (read-only; inference is NOT re-run)", flush=True)

    missing = [p for p in (PREDICTIONS, RESULTS, COMPARISON, PROTOCOL) if not p.exists()]
    if missing:
        for p in missing:
            print(f"MISSING sealed artifact: {p.relative_to(ROOT)}", flush=True)
        return 2
    print("Sealed artifacts present: predictions, results, comparison, protocol freeze", flush=True)

    groups: dict[tuple[str, str], dict[str, list[float]]] = defaultdict(
        lambda: {"actual": [], "prediction": []})
    with PREDICTIONS.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            g = groups[(row["target"], row["model"])]
            g["actual"].append(float(row["actual"]))
            g["prediction"].append(float(row["prediction"]))

    recorded: dict[tuple[str, str], dict[str, float]] = {}
    with RESULTS.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            recorded[(row["Target"], row["Model"])] = {
                "MAE": float(row["MAE"]), "RMSE": float(row["RMSE"]),
                "sMAPE": float(row["sMAPE"]), "nMAE": float(row["nMAE"]),
                "nRMSE": float(row["nRMSE"]),
            }

    failures = 0
    for key in sorted(groups):
        g = groups[key]
        recomputed = {
            "MAE": mae(g["actual"], g["prediction"]),
            "RMSE": rmse(g["actual"], g["prediction"]),
            "sMAPE": smape(g["actual"], g["prediction"]),
            "nMAE": nmae(g["actual"], g["prediction"]),
            "nRMSE": nrmse(g["actual"], g["prediction"]),
        }
        target, model = key
        rec = recorded.get((target, model))
        if rec is None:
            print(f"  {target}/{model}: no recorded metrics row found", flush=True)
            failures += 1
            continue
        bad = [m for m in recomputed
               if not math.isclose(recomputed[m], rec[m], rel_tol=TOLERANCE, abs_tol=TOLERANCE)]
        if bad:
            failures += 1
            detail = ", ".join(f"{m}: recomputed {recomputed[m]:.6f} != recorded {rec[m]:.6f}" for m in bad)
            print(f"  FAIL {target}/{model} (n={len(g['actual'])}): {detail}", flush=True)
        else:
            print(f"  OK   {target}/{model} (n={len(g['actual'])}) MAE={recomputed['MAE']:.4f}", flush=True)

    if failures:
        print(f"VERIFICATION FAILED: {failures} group(s) mismatched", flush=True)
        return 1
    print("VERIFICATION PASSED: sealed final-evaluation artifacts are internally consistent.", flush=True)
    print("Canonical runner: scripts/run_phase19_final_evaluation.py (do not re-run inference ad hoc).", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
