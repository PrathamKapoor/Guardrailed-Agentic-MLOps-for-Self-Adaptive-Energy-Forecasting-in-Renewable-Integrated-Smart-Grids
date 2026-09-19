"""Phase 19 final-test evaluation engine.

Executes the frozen final-test comparison plan
(``artifacts/experimental_design/final_test_comparison_plan.yaml``) against the
locked TEST partition (2020-11-01 .. 2020-12-31) under
``AccessMode.FINAL_EVALUATION`` with ``configuration_frozen=True``.

Design contracts honoured here:

- The frozen plan file is never modified; its SHA-256 is verified before use.
- Every test-partition timestamp access passes through
  :func:`authorize_final_evaluation`.
- Training windows for test folds never include test targets (walk-forward by
  calendar month, direct continuation of the phase 6/10 fold design).
- Model configurations are loaded exclusively from frozen artifacts:
  * classical reference hyperparameters: phase_10 ablation protocol freeze,
  * MLP challenger hyperparameters: phase_09 HPO best_configs,
  * feature-set definitions: config/ablation/phase_10.yaml.
- Deterministic seeds; torch runs with deterministic algorithms.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import torch
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from torch import nn

from ..baselines.base import timestamp_lag_value
from ..experimental_design.metrics import mae, nmae, nrmse, rmse, smape
from ..experimental_design.protocol import (
    AccessMode,
    ProtocolAccessError,
    authorize_partition,
    partition_for_timestamp,
)
from ..experimental_design.schemas import TRAIN_START

METRICS = ("MAE", "RMSE", "sMAPE", "nMAE", "nRMSE")
MLP_SEEDS = (42, 123, 2020, 2025, 31415)
CLASSICAL_SEED = 42


class FrozenPlanIntegrityError(ProtocolAccessError):
    """The frozen plan is missing, tampered with, or in an unexpected state."""


@dataclass(frozen=True)
class TestFold:
    """Monthly walk-forward fold over the locked test partition."""

    fold_id: str
    training_start: datetime
    training_end_exclusive: datetime
    eval_start: datetime
    eval_end_exclusive: datetime


def test_fold_boundaries() -> list[TestFold]:
    """November and December 2020 folds continuing F01..F10 numbering."""
    folds = []
    for index, month in enumerate((11, 12), start=11):
        start = datetime(2020, month, 1)
        end = datetime(2020, month + 1, 1) if month < 12 else datetime(2021, 1, 1)
        folds.append(
            TestFold(
                fold_id=f"F{index:02d}",
                training_start=TRAIN_START,
                training_end_exclusive=start,
                eval_start=start,
                eval_end_exclusive=end,
            )
        )
    return folds


def verify_frozen_plan(plan_path: Path) -> dict:
    """Load the plan and verify its SHA-256 against the repository sidecar."""
    sidecar = plan_path.parent / (plan_path.stem + ".sha256")
    if not plan_path.exists() or not sidecar.exists():
        raise FrozenPlanIntegrityError(f"frozen plan or checksum sidecar missing: {plan_path}")
    digest = hashlib.sha256(plan_path.read_bytes()).hexdigest()
    expected = sidecar.read_text(encoding="utf-8").split()[0].strip()
    if digest != expected:
        raise FrozenPlanIntegrityError(
            f"frozen plan checksum mismatch: expected {expected}, found {digest}"
        )
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    status = plan.get("status")
    if status not in ("FROZEN_NOT_EXECUTED", "FROZEN_EXECUTED"):
        raise FrozenPlanIntegrityError(f"unexpected frozen-plan status: {status!r}")
    return plan


def authorize_final_evaluation(timestamps: list[datetime], *, configuration_frozen: bool) -> None:
    """Gate every test-partition access behind the FINAL_EVALUATION mode."""
    if not configuration_frozen:
        raise ProtocolAccessError(
            "final-test target access requires an explicitly frozen configuration"
        )
    for timestamp in timestamps:
        authorize_partition(
            partition_for_timestamp(timestamp),
            AccessMode.FINAL_EVALUATION,
            configuration_frozen=True,
        )


def daily_persistence_prediction(
    actual_values: dict[datetime, float], row: dict
) -> float:
    """H24 daily persistence: actual value observed 24 hours earlier."""
    value, _ = timestamp_lag_value(actual_values, row["target_timestamp"], 24, row["forecast_origin"])
    return float(value)


def fit_predict_classical(
    model_kind: str,
    hyperparameters: dict,
    feature_names: list[str],
    train_rows: list[dict],
    y_train: list[float],
    eval_rows: list[dict],
) -> np.ndarray:
    """Refit a frozen classical configuration exactly as the phase-10 runner did."""
    x_train = [[row[name] for name in feature_names] for row in train_rows]
    x_eval = [[row[name] for name in feature_names] for row in eval_rows]
    if model_kind == "random_forest":
        model = RandomForestRegressor(**hyperparameters)
    elif model_kind == "hist_gradient_boosting":
        model = HistGradientBoostingRegressor(**hyperparameters)
    else:
        raise ValueError(f"unsupported frozen classical model kind: {model_kind}")
    model.fit(x_train, y_train)
    return model.predict(x_eval)


def fit_predict_mlp(
    hyperparameters: dict,
    feature_names: list[str],
    train_rows: list[dict],
    y_train: list[float],
    eval_rows: list[dict],
    seed: int,
) -> tuple[np.ndarray, int]:
    """Refit the HPO-tuned MLP exactly as the phase-10 confirmation runner did.

    Returns (predictions, epochs_run). Replicates: StandardScaler on X and y,
    chronological inner tail (last 10%) for early stopping, maximum 12 epochs,
    patience 4, restore-best state.
    """
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.use_deterministic_algorithms(True, warn_only=True)
    x_scaler, y_scaler = StandardScaler(), StandardScaler()
    x_train = x_scaler.fit_transform(
        np.array([[row[name] for name in feature_names] for row in train_rows], dtype=np.float32)
    )
    x_eval = x_scaler.transform(
        np.array([[row[name] for name in feature_names] for row in eval_rows], dtype=np.float32)
    )
    y_scaled = y_scaler.fit_transform(
        np.array(y_train, dtype=np.float32).reshape(-1, 1)
    ).ravel()
    split = max(1, int(0.9 * len(train_rows)))
    hidden_width = int(hyperparameters["hidden_width"])
    dropout = float(hyperparameters["dropout"])
    from ..models.neural.base import MLP

    model = MLP(len(feature_names), (hidden_width, 32), dropout)
    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=float(hyperparameters["learning_rate"]),
        weight_decay=float(hyperparameters["weight_decay"]),
    )
    loss_fn = nn.MSELoss()
    best = float("inf")
    state = None
    patience = 0
    epoch = 0
    for epoch in range(1, 13):
        model.train()
        optimizer.zero_grad()
        out = model(torch.tensor(x_train[:split]))
        loss = loss_fn(out, torch.tensor(y_scaled[:split]))
        loss.backward()
        optimizer.step()
        model.eval()
        with torch.no_grad():
            inner_val_loss = float(loss_fn(model(torch.tensor(x_train[split:])), torch.tensor(y_scaled[split:])))
        if inner_val_loss < best:
            best = inner_val_loss
            state = {key: value.clone() for key, value in model.state_dict().items()}
            patience = 0
        else:
            patience += 1
        if patience >= 4:
            break
    assert state is not None
    model.load_state_dict(state)
    with torch.no_grad():
        scaled = model(torch.tensor(x_eval)).numpy().ravel()
    predictions = y_scaler.inverse_transform(scaled.reshape(-1, 1)).ravel()
    return predictions, epoch


def diebold_mariano(
    loss_a: list[float] | np.ndarray,
    loss_b: list[float] | np.ndarray,
    horizon_lag: int = 23,
) -> tuple[float, float]:
    """Two-sided DM test on loss differentials with Newey-West variance.

    ``horizon_lag`` defaults to h-1 for h-step-ahead forecasts (23 for h24).
    Returns (statistic, p_value) using the standard normal approximation.
    """
    d = np.asarray(loss_a, dtype=float) - np.asarray(loss_b, dtype=float)
    n = len(d)
    if n == 0:
        raise ValueError("empty loss differential")
    d_bar = float(d.mean())
    centered = d - d_bar
    gamma0 = float(np.dot(centered, centered)) / n
    max_lag = min(horizon_lag, n - 1)
    variance = gamma0
    for lag in range(1, max_lag + 1):
        covariance = float(np.dot(centered[:-lag], centered[lag:])) / n
        variance += 2.0 * covariance
    floor = 1e-12 + 1e-12 * abs(gamma0)
    if variance <= 0:
        variance = floor
    statistic = d_bar / math.sqrt(variance / n)
    p_value = math.erfc(abs(statistic) / math.sqrt(2.0))
    return statistic, p_value


def holm_bonferroni(p_values: dict[str, float], alpha: float = 0.05) -> dict[str, dict]:
    """Step-down Holm-Bonferroni across a hypothesis family."""
    order = sorted(p_values, key=lambda key: p_values[key])
    total = len(order)
    decisions: dict[str, dict] = {}
    rejected_so_far = True
    for index, key in enumerate(order):
        p_value = p_values[key]
        threshold = alpha / (total - index)
        reject = bool(rejected_so_far and p_value <= threshold)
        if not reject:
            rejected_so_far = False
        decisions[key] = {
            "p_value": p_value,
            "holm_threshold": threshold,
            "reject_null_at_alpha": reject,
        }
    return decisions


def _metrics_block(actual: list[float], predicted: list[float]) -> dict[str, float]:
    return {
        "MAE": mae(actual, predicted),
        "RMSE": rmse(actual, predicted),
        "sMAPE": smape(actual, predicted),
        "nMAE": nmae(actual, predicted),
        "nRMSE": nrmse(actual, predicted),
    }


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def evaluate_plan(
    root: Path,
    *,
    targets: tuple[str, ...] = ("load", "wind", "pv"),
    smoke: bool = False,
) -> dict:
    """Run the frozen comparison evaluation for the requested targets.

    Returns a result dictionary; the caller decides what to persist. When
    ``smoke`` is true a reduced run (single fold, first seed only for the MLP)
    is executed purely to validate plumbing; results are flagged NON_EVIDENCE.
    """
    plan = verify_frozen_plan(root / "artifacts/experimental_design/final_test_comparison_plan.yaml")
    if "final_test_authorization_required" not in plan:
        raise FrozenPlanIntegrityError("frozen plan lacks authorization marker")
    ablation_config = _load_json(root / "config/ablation/phase_10.yaml")
    protocol_freeze = _load_json(
        root / "artifacts/experimental_design/phase_10_ablation_protocol_freeze.yaml"
    )

    target_columns = {
        "load": ("load_hourly.parquet", "actual_system_load"),
        "wind": ("wind_hourly.parquet", "actual_wind"),
        "pv": ("pv_hourly.parquet", "actual_pv"),
    }

    results: dict = {"status": "NON_EVIDENCE_SMOKE" if smoke else "FINAL_EVALUATION_VALID",
                     "plan_sha256_verified": True, "configuration_frozen": True,
                     "targets": {}, "generated_at": datetime.now().isoformat()}
    folds = test_fold_boundaries()[:1] if smoke else test_fold_boundaries()

    for target in targets:
        entry = plan["matrix"][target]
        reference_spec = entry["reference_model"]
        challenger_spec = entry["challengers"][0]
        baseline_id = entry["baseline_comparator"]

        classical_kind = protocol_freeze["classical_models"][target]["model"]
        classical_params = protocol_freeze["classical_models"][target]["hyperparameters"]
        mlp_params = _load_json(
            root / f"artifacts/experiments/hpo/phase_09/best_configs/{target}_pytorch_mlp.yaml"
        )["hyperparameters"]
        reference_features = ablation_config["feature_sets"][reference_spec["feature_set"]]
        challenger_features = ablation_config["feature_sets"][challenger_spec["feature_set"]]

        filename, actual_column = target_columns[target]
        canonical = pq.read_table(
            root / "data/processed" / filename
        ).to_pylist()
        actual_values = {row["timestamp"]: float(row[actual_column]) for row in canonical}
        day_ahead_values = None
        if baseline_id == "RTS_DAY_AHEAD":
            day_ahead_column = {
                "load": "day_ahead_system_load",
                "wind": "day_ahead_wind",
                "pv": "day_ahead_pv",
            }[target]
            day_ahead_values = {row["timestamp"]: float(row[day_ahead_column]) for row in canonical}

        feature_rows = pq.read_table(
            root / f"data/processed/features/{target}/h24/combined_v1.parquet",
            columns=["forecast_origin", "target_timestamp", *sorted(set(reference_features + challenger_features))],
        ).to_pylist()

        per_fold = []
        prediction_records: list[dict] = []
        for fold in folds:
            train_rows = [r for r in feature_rows if r["target_timestamp"] < fold.training_end_exclusive]
            eval_rows = [
                r for r in feature_rows if fold.eval_start <= r["target_timestamp"] < fold.eval_end_exclusive
            ]
            eval_timestamps = [r["target_timestamp"] for r in eval_rows]
            authorize_final_evaluation(eval_timestamps, configuration_frozen=True)

            common = set(eval_timestamps)
            if day_ahead_values is not None:
                common &= {ts for ts in common if ts in day_ahead_values}
            persistence_available = {
                r["target_timestamp"]
                for r in eval_rows
                if (r["target_timestamp"] - timedelta(hours=24)) in actual_values
            }
            common &= persistence_available
            common_rows = sorted((r for r in eval_rows if r["target_timestamp"] in common), key=lambda r: r["target_timestamp"])
            common_ts = [r["target_timestamp"] for r in common_rows]

            y_train = [actual_values[r["target_timestamp"]] for r in train_rows]

            reference_predictions = fit_predict_classical(
                classical_kind, classical_params, reference_features, train_rows, y_train, common_rows
            )
            mlp_seeds = MLP_SEEDS[:1] if smoke else MLP_SEEDS
            seed_predictions = []
            epochs_seen = []
            for seed in mlp_seeds:
                predictions, epochs = fit_predict_mlp(
                    mlp_params, challenger_features, train_rows, y_train, common_rows, seed
                )
                seed_predictions.append(predictions)
                epochs_seen.append(epochs)
            challenger_predictions = np.mean(np.vstack(seed_predictions), axis=0)

            baseline_predictions = []
            for row in common_rows:
                if baseline_id == "RTS_DAY_AHEAD":
                    baseline_predictions.append(day_ahead_values[row["target_timestamp"]])
                elif baseline_id == "H24_DAILY_PERSISTENCE":
                    baseline_predictions.append(daily_persistence_prediction(actual_values, row))
                else:
                    raise ValueError(f"unsupported baseline comparator: {baseline_id}")

            for index, row in enumerate(common_rows):
                record_base = {
                    "fold_id": fold.fold_id,
                    "target": target,
                    "forecast_origin": row["forecast_origin"],
                    "target_timestamp": row["target_timestamp"],
                    "actual": actual_values[row["target_timestamp"]],
                }
                for name, values in (
                    ("reference", reference_predictions),
                    ("challenger", challenger_predictions),
                    ("baseline", baseline_predictions),
                ):
                    prediction = float(values[index])
                    error = record_base["actual"] - prediction
                    prediction_records.append(
                        {**record_base, "configuration": name, "prediction": prediction,
                         "absolute_error": abs(error), "squared_error": error ** 2}
                    )

            per_fold.append(
                {
                    "fold_id": fold.fold_id,
                    "eval_samples": len(common_rows),
                    "training_samples": len(train_rows),
                    "mlp_seeds_used": list(mlp_seeds),
                    "mlp_epochs_by_seed": epochs_seen,
                }
            )

        combined = prediction_records
        by_config: dict[str, dict[str, list]] = {}
        for record in combined:
            bucket = by_config.setdefault(record["configuration"], {"actual": [], "prediction": [], "abs": [], "sq": []})
            bucket["actual"].append(record["actual"])
            bucket["prediction"].append(record["prediction"])
            bucket["abs"].append(record["absolute_error"])
            bucket["sq"].append(record["squared_error"])

        metrics_table = {}
        for name, bucket in by_config.items():
            metrics_table[name] = {
                "samples": len(bucket["actual"]),
                **_metrics_block(bucket["actual"], bucket["prediction"]),
            }

        tests: dict = {}
        if {"reference", "baseline"} <= set(by_config):
            statistic, p_value = diebold_mariano(by_config["reference"]["abs"], by_config["baseline"]["abs"])
            tests[f"FT-H1-{target.upper()}"] = {
                "comparison": "reference_vs_baseline_comparator",
                "dm_statistic": statistic,
                "p_value": p_value,
            }
        if {"reference", "challenger"} <= set(by_config):
            statistic, p_value = diebold_mariano(by_config["reference"]["abs"], by_config["challenger"]["abs"])
            tests[f"FT-H2-{target.upper()}"] = {
                "comparison": "reference_vs_challenger",
                "dm_statistic": statistic,
                "p_value": p_value,
            }

        results["targets"][target] = {
            "reference_model": reference_spec["candidate_id"],
            "challenger_model": challenger_spec["candidate_id"],
            "baseline_comparator": baseline_id,
            "folds": per_fold,
            "metrics": metrics_table,
            "tests_raw": tests,
            "prediction_records": prediction_records,
        }

    family = {}
    for target in targets:
        for key, value in results["targets"][target]["tests_raw"].items():
            if key.startswith("FT-H1-"):
                family[key] = value["p_value"]
    holm = holm_bonferroni(family)
    for target in targets:
        key = f"FT-H1-{target.upper()}"
        if key in results["targets"][target]["tests_raw"]:
            results["targets"][target]["tests_raw"][key]["holm_decision"] = holm[key]
    results["holm_bonferroni_primary_family"] = holm
    return results


def write_results(root: Path, results: dict, destination: Path) -> dict:
    """Persist evaluation outputs (CSV/JSON/parquet) under ``destination``."""
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "metrics").mkdir(exist_ok=True)
    (destination / "manifests").mkdir(exist_ok=True)

    summary = {
        "status": results["status"],
        "configuration_frozen": results["configuration_frozen"],
        "plan_sha256_verified": results["plan_sha256_verified"],
        "generated_at": results["generated_at"],
        "targets": {},
    }
    metric_rows: list[dict] = []
    prediction_rows: list[dict] = []
    for target, entry in results["targets"].items():
        tests = entry["tests_raw"]
        summary["targets"][target] = {
            "reference_model": entry["reference_model"],
            "baseline_comparator": entry["baseline_comparator"],
            "metrics": entry["metrics"],
            "primary_test": tests.get(f"FT-H1-{target.upper()}"),
            "folds": entry["folds"],
        }
        for configuration, block in entry["metrics"].items():
            metric_rows.append({"target": target, "configuration": configuration, **block})
        for record in entry["prediction_records"]:
            prediction_rows.append({
                key: (str(value) if isinstance(value, datetime) else value)
                for key, value in record.items()
            })
    primary_p_values = results.get("holm_bonferroni_primary_family", {})
    (destination / "metrics" / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )
    (destination / "metrics" / "holm_bonferroni.json").write_text(
        json.dumps(primary_p_values, indent=2, sort_keys=True), encoding="utf-8"
    )
    with (destination / "metrics" / "final_test_metrics.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["target", "configuration", *METRICS, "samples"])
        writer.writeheader()
        writer.writerows(metric_rows)

    predictions_path = destination / "predictions" / "final_test_predictions.parquet"
    predictions_path.parent.mkdir(exist_ok=True)
    pq.write_table(pa.Table.from_pylist(prediction_rows), predictions_path)

    manifest = {
        "artifact_dir": str(destination),
        "targets": sorted(results["targets"]),
        "status": results["status"],
    }
    (destination / "manifests" / "run_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )
    return summary
