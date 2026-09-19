from __future__ import annotations

import hashlib, json, sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"));sys.path.insert(0,str(ROOT/"scripts"))
from smartgrid_mlops.experimental_design.metrics import mae,nmae,nrmse,rmse,smape
from smartgrid_mlops.experimental_design.protocol import AccessMode,ProtocolAccessError,authorize_partition,partition_for_timestamp
from smartgrid_mlops.experimental_design.rolling_origin import fold_boundaries,fold_membership
from smartgrid_mlops.experimental_design.seeds import MASTER_SEEDS,seeds_for
from smartgrid_mlops.experimental_design.splits import load_feature_rows,split_rows
from smartgrid_mlops.experimental_design.validation import validate_historical_context,validate_temporal_order

def feature(target="load",horizon=24): return ROOT/f"data/processed/features/{target}/h{horizon}/combined_v1.parquet"

def test_target_timestamp_boundary_controls_h24_partition():
    origin=datetime(2020,10,31);target=origin+timedelta(hours=24)
    assert partition_for_timestamp(target)=="TEST"

@pytest.mark.parametrize("horizon,train,validation,test",[(1,5687,1464,1464),(24,5664,1464,1464)])
def test_actual_horizon_partition_counts(horizon,train,validation,test):
    parts=split_rows(load_feature_rows(feature(horizon=horizon)))
    assert tuple(map(len,(parts["TRAIN"],parts["VALIDATION"],parts["TEST"])))==(train,validation,test)

def test_final_test_access_is_locked_during_selection():
    with pytest.raises(ProtocolAccessError): authorize_partition("TEST",AccessMode.MODEL_SELECTION)
    with pytest.raises(ProtocolAccessError): authorize_partition("TEST",AccessMode.FINAL_EVALUATION,configuration_frozen=False)
    authorize_partition("TEST",AccessMode.FINAL_EVALUATION,configuration_frozen=True)

def test_historical_context_before_origin_is_allowed():
    validate_historical_context(datetime(2020,10,31,23),datetime(2020,11,1,0))
    with pytest.raises(ValueError): validate_historical_context(datetime(2020,11,1,1),datetime(2020,11,1,0))

def test_rolling_folds_are_ordered_and_pretest():
    rows=load_feature_rows(feature())
    for boundary in fold_boundaries():
        train,validation=fold_membership(rows,boundary);validate_temporal_order(train,validation)
        assert max(r["target_timestamp"] for r in validation)<datetime(2020,11,1)

def test_no_development_test_overlap():
    parts=split_rows(load_feature_rows(feature()))
    development=parts["TRAIN"]+parts["VALIDATION"]
    assert max(r["target_timestamp"] for r in development)<min(r["target_timestamp"] for r in parts["TEST"])

def test_metrics_perfect_constant_and_zero_safe():
    assert mae([1,2],[1,2])==rmse([1,2],[1,2])==smape([0,2],[0,2])==0
    assert mae([1,2],[2,3])==1 and rmse([1,2],[2,3])==1
    assert smape([0,0],[0,1])==100
    assert nmae([1,3],[2,4])==.5 and nrmse([1,3],[2,4])==.5

def test_seed_policy_is_fixed_and_deterministic_models_run_once():
    assert MASTER_SEEDS==(42,123,2020,2025,31415)
    assert seeds_for(True)==MASTER_SEEDS and seeds_for(False)==(None,)

def test_protocol_freeze_schema_and_checksum():
    path=ROOT/"artifacts/experimental_design/protocol_freeze.yaml";data=json.loads(path.read_text())
    required={"protocol_version","dataset_version","feature_manifest_checksum","primary_horizon","secondary_horizon","train_window","validation_window","test_window","final_test_status","primary_metric","seed_policy","significance_level","multiple_comparison_policy"}
    assert required<=data.keys() and data["final_test_status"]=="LOCKED" and data["model_results_observed"] is False
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    recorded=(ROOT/"artifacts/experimental_design/protocol_freeze.sha256").read_text().split()[0]
    assert digest==recorded

def test_split_generation_is_deterministic():
    from build_experimental_splits import build_all
    first=build_all();second=build_all()
    assert first["rolling_checksum"]==second["rolling_checksum"]
    assert [item["split_checksum"] for item in first["manifests"]]==[item["split_checksum"] for item in second["manifests"]]

def test_manifest_counts_and_final_lock():
    paths=sorted((ROOT/"artifacts/experimental_design").glob("split_manifest_*"));assert len(paths)==6
    for path in paths:
        manifest=json.loads(path.read_text());assert manifest["final_test_status"]=="LOCKED" and manifest["test_samples"]==1464
