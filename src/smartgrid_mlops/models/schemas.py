from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelSpecification:
    family: str
    parameters: dict
    stochastic: bool
    uses_feature_scaling: bool
