"""Bounded expanding-window refit of the frozen reference specification.

No HPO, no feature selection, no model-family selection: the challenger reuses
the exact Phase 10/11 frozen implementation, hyperparameters, feature
specification, scaling policy, and single deterministic seed."""
from __future__ import annotations
import json, time
from datetime import datetime
from pathlib import Path
import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from smartgrid_mlops.mlops.fingerprints import fingerprint

FEATURE_NAMES = ["lag_1", "lag_24", "lag_168"]


def load_reference_spec(root: Path, target: str) -> dict:
    """Frozen reference specification from the Phase 10 protocol freeze."""
    phase10 = json.loads((root / "artifacts/experimental_design/phase_10_ablation_protocol_freeze.yaml").read_text())
    entry = phase10["classical_models"][target]
    return {"model_family": entry["model"], "implementation_id": entry["implementation_id"],
            "hyperparameters": dict(entry["hyperparameters"])}


def reference_model_spec_document(root: Path, target: str, feature_doc: dict) -> dict:
    """Same construction as build_phase12_mlops_foundation so the challenger's
    model_spec_fingerprint equals the parent reference fingerprint."""
    ref = json.loads((root / "artifacts/model_registry/forecasting_reference_registry.yaml").read_text())[target]["reference_model"]
    spec = load_reference_spec(root, target)
    return {"model_family": spec["model_family"], "framework": ref["framework"],
            "implementation_id": ref["implementation_id"], "feature_specification": feature_doc,
            "hyperparameters": spec["hyperparameters"], "scaling_policy": "none for tree estimator",
            "training_policy": {"folds": ["F05", "F06"], "seed_policy": [42],
                                "selection_source": "Phase 10 freeze"},
            "horizon": 24}


def build_estimator(model_family: str, hyperparameters: dict, seed: int):
    if model_family == "random_forest":
        params = {k: v for k, v in hyperparameters.items() if k not in ("n_jobs", "random_state")}
        return RandomForestRegressor(**params, random_state=seed, n_jobs=-1)
    if model_family == "hist_gradient_boosting":
        params = {k: v for k, v in hyperparameters.items() if k != "random_state"}
        return HistGradientBoostingRegressor(**params, random_state=seed)
    raise ValueError(f"Model family {model_family} is not allowed by the frozen retraining policy")


def fit_rows(rows, *, model_family: str, hyperparameters: dict, seed: int):
    X = np.asarray([[r[name] for name in FEATURE_NAMES] for r in rows], dtype=float)
    y = np.asarray([r["target"] for r in rows], dtype=float)
    model = build_estimator(model_family, hyperparameters, seed)
    start = time.perf_counter()
    model.fit(X, y)
    return model, time.perf_counter() - start


def predict_rows(model, rows) -> np.ndarray:
    X = np.asarray([[r[name] for name in FEATURE_NAMES] for r in rows], dtype=float)
    return np.asarray(model.predict(X), dtype=float)


def model_instance_fingerprint(*, model_spec_fingerprint: str, training_dataset_fingerprint: str,
                               training_cutoff: datetime, seed: int) -> str:
    return fingerprint({"model_spec_fingerprint": model_spec_fingerprint,
                        "training_dataset_fingerprint": training_dataset_fingerprint,
                        "training_cutoff": training_cutoff.isoformat(), "seed": seed},
                       "model-instance-v1")
