from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

PROTOCOL_VERSION = "rts_gmlc_exp_protocol_v1"
TRAIN_START = datetime(2020, 1, 1)
VALIDATION_START = datetime(2020, 9, 1)
TEST_START = datetime(2020, 11, 1)
DATA_END_EXCLUSIVE = datetime(2021, 1, 1)

@dataclass(frozen=True)
class ExperimentMetadata:
    experiment_id: str
    target: str
    horizon: int
    model_family: str
    feature_set: str
    dataset_version: str
    feature_version: str
    training_window: str
    validation_window: str
    test_window: str
    fold_id: str
    seed: int | None
    hyperparameters: dict
    metrics: dict
    runtime_seconds: float | None
    software_version: str
    artifact_checksum: str
