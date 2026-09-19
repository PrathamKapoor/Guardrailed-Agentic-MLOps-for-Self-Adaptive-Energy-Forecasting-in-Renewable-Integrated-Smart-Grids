from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

import pytest
from sklearn.pipeline import Pipeline

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from smartgrid_mlops.models.factory import create_model, is_stochastic, load_config
from smartgrid_mlops.models.validation import reject_final_test


def test_fixed_model_config_and_factory_cover_frozen_families():
    config=load_config(); assert config["no_hyperparameter_optimization"] is True
    assert set(config["models"])=={"linear_regression","ridge","random_forest","extra_trees","hist_gradient_boosting"}
    assert all(hasattr(create_model(family,42,config),"fit") for family in config["models"])


def test_ridge_scaling_is_training_pipeline_and_trees_are_unscaled():
    ridge=create_model("ridge"); assert isinstance(ridge,Pipeline) and "scaler" in ridge.named_steps
    assert not isinstance(create_model("random_forest",42),Pipeline)
    assert not isinstance(create_model("extra_trees",42),Pipeline)


def test_seed_policy_and_deterministic_model_reproducibility():
    assert is_stochastic("random_forest") and is_stochastic("extra_trees") and not is_stochastic("ridge")
    x=[[0.0],[1.0],[2.0]];y=[0.0,1.0,2.0];a=create_model("linear_regression").fit(x,y).predict(x);b=create_model("linear_regression").fit(x,y).predict(x)
    assert list(a)==list(b)


def test_final_test_denial_and_no_runner_test_flag():
    with pytest.raises(PermissionError): reject_final_test(datetime(2020,11,1))
    text=(ROOT/"scripts/run_classical_experiments.py").read_text(); assert '"--test"' not in text and '"--unlock-test"' not in text


def test_phase7_protocol_checksum_and_prediction_schema():
    protocol=ROOT/"artifacts/experimental_design/phase_07_model_protocol_freeze.yaml"; recorded=(ROOT/"artifacts/experimental_design/phase_07_model_protocol_freeze.sha256").read_text().split()[0]
    assert hashlib.sha256(protocol.read_bytes()).hexdigest()==recorded
    manifest=json.loads((ROOT/"artifacts/experiments/classical/phase_07/classical_experiment_manifest.yaml").read_text());assert manifest["final_test_accessed"] is False
    import pyarrow.parquet as pq
    fields=set(pq.read_schema(ROOT/"artifacts/experiments/classical/phase_07/predictions/classical_predictions.parquet").names)
    assert {"experiment_id","target","horizon","model_family","fold_id","seed","forecast_origin","target_timestamp","actual","prediction","error","absolute_error","squared_error","baseline_reference"}<=fields
