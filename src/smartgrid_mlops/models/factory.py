from __future__ import annotations

import json
from pathlib import Path

from . import classical
from .schemas import ModelSpecification

ROOT = Path(__file__).resolve().parents[3]
STOCHASTIC = {"random_forest", "extra_trees"}
BUILDERS = {name: getattr(classical, name) for name in ("linear_regression", "ridge", "random_forest", "extra_trees", "hist_gradient_boosting")}


def load_config(path: Path | None = None) -> dict:
    return json.loads((path or ROOT / "config/models/classical_untuned_v1.yaml").read_text(encoding="utf-8"))


def is_stochastic(family: str) -> bool: return family in STOCHASTIC


def specification(family: str, config: dict | None = None) -> ModelSpecification:
    config = config or load_config(); return ModelSpecification(family, config["models"][family], is_stochastic(family), family == "ridge")


def create_model(family: str, seed: int | None = None, config: dict | None = None):
    spec = specification(family, config)
    return BUILDERS[family](dict(spec.parameters), seed)
