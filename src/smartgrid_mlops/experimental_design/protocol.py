from __future__ import annotations

from enum import Enum
from datetime import datetime
from .schemas import TRAIN_START, VALIDATION_START, TEST_START, DATA_END_EXCLUSIVE

class AccessMode(str, Enum):
    TRAINING = "TRAINING"
    VALIDATION = "VALIDATION"
    MODEL_SELECTION = "MODEL_SELECTION"
    FINAL_EVALUATION = "FINAL_EVALUATION"

class ProtocolAccessError(PermissionError):
    """Raised when an access mode attempts to touch a partition it may not see.

    Enforces the protocol-freeze boundary: development modes cannot read the
    TEST partition; only FINAL_EVALUATION mode may, after the candidate is
    frozen and the protocol unsealed.
    """

    default_detail = "protocol access violation: partition not visible in this access mode"

    def __init__(self, detail: str | None = None) -> None:
        super().__init__(detail or self.default_detail)

def partition_for_timestamp(target_timestamp: datetime) -> str:
    if TRAIN_START <= target_timestamp < VALIDATION_START: return "TRAIN"
    if VALIDATION_START <= target_timestamp < TEST_START: return "VALIDATION"
    if TEST_START <= target_timestamp < DATA_END_EXCLUSIVE: return "TEST"
    return "OUTSIDE"

def authorize_partition(partition: str, mode: AccessMode, configuration_frozen: bool = False) -> None:
    allowed = {
        AccessMode.TRAINING: {"TRAIN"},
        AccessMode.VALIDATION: {"TRAIN", "VALIDATION"},
        AccessMode.MODEL_SELECTION: {"TRAIN", "VALIDATION"},
        AccessMode.FINAL_EVALUATION: {"TRAIN", "VALIDATION", "TEST"} if configuration_frozen else {"TRAIN", "VALIDATION"},
    }
    if partition not in allowed[mode]:
        raise ProtocolAccessError(f"{mode.value} may not access {partition} targets; final configuration frozen={configuration_frozen}")

def experiment_id(target: str, horizon: int, model: str, feature_set: str, seed: int | None, fold: int) -> str:
    seed_token = "DET" if seed is None else f"S{seed}"
    return f"{target.upper()}-H{horizon}-{model.upper()}-{feature_set.upper()}-{seed_token}-F{fold:02d}"
