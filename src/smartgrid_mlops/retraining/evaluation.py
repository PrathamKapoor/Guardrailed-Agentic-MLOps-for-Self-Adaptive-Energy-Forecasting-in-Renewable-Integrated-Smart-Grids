"""Post-retraining evaluation on matched development timestamps.

Primary comparison: challenger vs frozen reference on identical synthetic
post-drift timestamps. Clean counterfactual measures whether adapting to the
synthetic drift degrades performance under the original stream. This is
simulation evidence only and does not control promotion."""
from __future__ import annotations
import numpy as np
from smartgrid_mlops.experimental_design.metrics import mae, rmse, smape, nmae, nrmse


def evaluate_predictions(actual, predicted) -> dict:
    actual = np.asarray(actual, dtype=float); predicted = np.asarray(predicted, dtype=float)
    if not np.all(np.isfinite(predicted)):
        raise ValueError("Non-finite model outputs are not evaluable")
    return {"MAE": float(mae(actual, predicted)), "RMSE": float(rmse(actual, predicted)),
            "sMAPE": float(smape(actual, predicted)), "nMAE": float(nmae(actual, predicted)),
            "nRMSE": float(nrmse(actual, predicted)), "rows": int(len(actual))}


def matched_evaluation(rows, reference_predictions, challenger_predictions) -> dict:
    if not (len(rows) == len(reference_predictions) == len(challenger_predictions)):
        raise ValueError("evaluation requires matched timestamps")
    actual = [r["target"] for r in rows]
    return {"reference": evaluate_predictions(actual, reference_predictions),
            "challenger": evaluate_predictions(actual, challenger_predictions),
            "evaluation_rows": len(rows),
            "window_start": rows[0]["target_timestamp"].isoformat(),
            "window_end": rows[-1]["target_timestamp"].isoformat()}


def adaptation_gain_percent(reference_mae: float, challenger_mae: float) -> float:
    return 100.0 * (reference_mae - challenger_mae) / reference_mae if reference_mae else 0.0


def clean_stability_change_percent(clean_reference_mae: float, clean_challenger_mae: float) -> float:
    return 100.0 * (clean_reference_mae - clean_challenger_mae) / clean_reference_mae if clean_reference_mae else 0.0
