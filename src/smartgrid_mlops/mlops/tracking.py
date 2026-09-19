from __future__ import annotations

import json
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

import mlflow
from mlflow import MlflowClient

from .schemas import FINAL_TEST_TAGS
from .validation import portable_path


@dataclass(frozen=True)
class TrackingConfig:
    project_root: Path
    tracking_db: str = "artifacts/mlflow/phase12_tracking.db"
    artifact_root: str = "artifacts/mlflow/phase12_artifacts"

    def __post_init__(self):
        portable_path(self.tracking_db); portable_path(self.artifact_root)

    @property
    def tracking_uri(self) -> str:
        path = (self.project_root / self.tracking_db).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{path.as_posix()}"

    @property
    def artifact_uri(self) -> str:
        path = (self.project_root / self.artifact_root).resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path.as_uri()

    def initialize(self) -> MlflowClient:
        mlflow.set_tracking_uri(self.tracking_uri)
        return MlflowClient(tracking_uri=self.tracking_uri)


def ensure_experiment(config: TrackingConfig, name: str) -> str:
    client = config.initialize()
    found = client.get_experiment_by_name(name)
    return found.experiment_id if found else client.create_experiment(name, artifact_location=config.artifact_uri)


@contextmanager
def tracked_run(config: TrackingConfig, experiment_name: str, *, tags: dict, params: dict | None = None,
                run_name: str | None = None):
    experiment_id = ensure_experiment(config, experiment_name)
    all_tags = {**FINAL_TEST_TAGS, **{k: str(v) for k, v in tags.items()}}
    with mlflow.start_run(experiment_id=experiment_id, run_name=run_name, tags=all_tags) as run:
        for key, value in (params or {}).items():
            mlflow.log_param(key, json.dumps(value, sort_keys=True) if isinstance(value, (dict, list)) else value)
        yield run
