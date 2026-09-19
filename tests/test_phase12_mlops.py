from __future__ import annotations
import json
from pathlib import Path
import pytest

from smartgrid_mlops.mlops.evidence import evidence_route
from smartgrid_mlops.mlops.fingerprints import feature_spec_fingerprint, model_spec_fingerprint, research_run_key
from smartgrid_mlops.mlops.lineage import LineageGraph
from smartgrid_mlops.mlops.importer import ImportRecord, import_records
from smartgrid_mlops.mlops.registry import RegistrationError, ResearchRegistry
from smartgrid_mlops.mlops.schemas import AuditEvent, FINAL_TEST_TAGS
from smartgrid_mlops.mlops.tracking import TrackingConfig, ensure_experiment
from smartgrid_mlops.mlops.validation import portable_path, resolve_portable_path

ROOT=Path(__file__).parents[1]

def model_spec(): return {"model_family":"random_forest","framework":"sklearn","implementation_id":"RF_V1","feature_specification":{"id":"B"},"hyperparameters":{"n":3},"scaling_policy":"none","training_policy":{"seed":42},"horizon":24}
def entry(fp,status="VALID",gate="BENCHMARK_GATE_FAIL"):
    return {"registry_id":"REF-X","target":"load","horizon":24,"research_role":"REFERENCE","registry_state":"REGISTERED_REFERENCE","model_family":"random_forest","framework":"sklearn","implementation_id":"RF_V1","model_spec_fingerprint":fp,"feature_set_id":"B","feature_spec_fingerprint":"feature-x","dataset_fingerprint":"dataset-x","protocol_hash":"protocol-x","development_primary_metric":"MAE","development_MAE":2.0,"strongest_benchmark":"BASE","benchmark_MAE":1.0,"development_benchmark_gate":gate,"evidence_status":status,"selection_evidence":["evidence.csv"],"deviation_references":[],"created_from_phase":"11","final_test_performance_status":"NOT_EVALUATED"}

def test_mlflow_tracking_initialization_and_relative_config(tmp_path):
    cfg=TrackingConfig(tmp_path);eid=ensure_experiment(cfg,"test/phase12")
    assert eid and "sqlite:///" in cfg.tracking_uri and not cfg.tracking_db.startswith(str(tmp_path))

def test_deterministic_research_run_key():
    args=dict(phase="09",target="load",horizon=24,model_spec_fingerprint="x",feature_set="B",fold="F01",seed=42,evaluation_role="HPO")
    assert research_run_key(**args)==research_run_key(**args)
    assert research_run_key(**args)!=research_run_key(**{**args,"seed":123})

def test_evidence_routing_valid_invalid_and_audit():
    assert evidence_route({"evidence_status":"VALID","framework":"sklearn","implementation_id":"RF"})=="OFFICIAL"
    assert evidence_route({"evidence_status":"INVALIDATED","framework":"sklearn","implementation_id":"MLPRegressor"})=="AUDIT_ONLY"
    assert evidence_route({"evidence_status":"NON_EVIDENCE_SMOKE"})=="EXCLUDED"
    assert evidence_route({"evidence_status":"VALID","model_family":"mlp","framework":"sklearn","implementation_id":"MLPRegressor"})=="REJECTED"

def test_historical_import_idempotency(tmp_path):
    for relative in ("artifacts/experimental_design/phase_07_model_protocol_freeze.yaml", "data/manifests/processed_dataset_manifest.yaml", "data/manifests/feature_manifest.yaml"):
        path=tmp_path/relative; path.parent.mkdir(parents=True,exist_ok=True); path.write_text("{}")
    record=ImportRecord("07","load",24,"random_forest","sklearn","RF","B","F01","42","VALIDATION","VALID",{"MAE":1.0},{},"metrics.csv").finalize()
    config=TrackingConfig(tmp_path)
    first=import_records(config,[record],tmp_path/"audit/events.jsonl")
    second=import_records(config,[record],tmp_path/"audit/events.jsonl")
    assert first["imported"]==1 and second["duplicates"]==1

def test_model_and_feature_fingerprint_determinism():
    spec=model_spec(); assert model_spec_fingerprint(spec)==model_spec_fingerprint(dict(reversed(list(spec.items()))))
    feature={"feature_set_id":"B","feature_names":["lag_1"],"transformations":"lag","forecast_horizon_availability_contract":"origin only","logical_feature_identity":"abc"}
    assert feature_spec_fingerprint(feature)==feature_spec_fingerprint(feature)
    assert feature_spec_fingerprint(feature)!=feature_spec_fingerprint({**feature,"feature_names":["lag_24"]})

def test_fingerprint_mismatch_and_invalidated_reference_rejected():
    fp=model_spec_fingerprint(model_spec()); reg=ResearchRegistry()
    with pytest.raises(RegistrationError,match="FINGERPRINT_MISMATCH"): reg.register(entry(fp),expected_model_fingerprint="wrong")
    with pytest.raises(RegistrationError,match="VALID"): reg.register(entry(fp,status="INVALIDATED"),expected_model_fingerprint=fp)

def test_reference_allowed_with_failed_benchmark_but_not_promotion_eligible():
    fp=model_spec_fingerprint(model_spec()); reg=ResearchRegistry(); record=entry(fp)
    reg.register(record,expected_model_fingerprint=fp)
    assert record["registry_state"]=="REGISTERED_REFERENCE"
    assert not reg.promotion_eligible(record)

def test_registry_schema_one_reference_and_challenger_import():
    registry=ResearchRegistry.load(ROOT/"artifacts/model_registry/mlops_research_registry.yaml")
    assert registry.validate_one_reference_per_target()
    assert {x["target"] for x in registry.entries if x["research_role"]=="REFERENCE"}=={"load","wind","pv"}
    assert len([x for x in registry.entries if x["research_role"]=="CHALLENGER"])==3

def test_lineage_traversal_and_missing_node_detection():
    graph=LineageGraph();graph.add_node("a","dataset");graph.add_node("b","processed_dataset");graph.add_edge("b","a","DERIVED_FROM")
    assert {x["id"] for x in graph.trace("b")}=={"a","b"}
    graph.edges.append({"source":"b","target":"missing","relationship":"USES"})
    with pytest.raises(ValueError,match="Missing lineage node"): graph.validate()

def test_repository_lineage_complete_for_all_references():
    graph=LineageGraph.load(ROOT/"artifacts/mlops/lineage/lineage_index.yaml")
    for target in ("LOAD","WIND","PV"):
        types={x["type"] for x in graph.trace(f"MLOPS-REF-{target}-H24-V1")}
        assert {"dataset","processed_dataset","feature_dataset","protocol","model_spec","evaluation","evidence","registry_entry"} <= types

def test_relative_path_portability(tmp_path):
    for root in (tmp_path/"device-a",tmp_path/"device-b"):
        expected=root/"artifacts/x.json";expected.parent.mkdir(parents=True);expected.write_text("{}")
        assert resolve_portable_path(root,"artifacts/x.json")==expected.resolve()
    with pytest.raises(ValueError): portable_path(r"C:\\Projects\\machine-specific")

def test_audit_event_schema_and_actor():
    event=AuditEvent("MODEL_REGISTERED","x","SYSTEM","12").to_dict()
    assert {"event_id","timestamp","event_type","subject_id","actor_type","phase","details","evidence_refs"} <= event.keys()
    assert event["actor_type"] in {"SYSTEM","IMPORTER"}

def test_final_test_access_metadata():
    assert FINAL_TEST_TAGS=={"final_test_training_access":"NO","final_test_hpo_access":"NO","final_test_selection_access":"NO","final_test_performance_access":"NO"}

def test_p9_dev_002_preserves_dual_binary_and_logical_provenance():
    graph=LineageGraph.load(ROOT/"artifacts/mlops/lineage/lineage_index.yaml");node=graph.nodes["deviation:P9-DEV-002"]
    assert node["scientific_integrity"]=="PASS"
    assert node["historical_binary_sha256"]!=node["current_binary_sha256"]
    assert len(node["logical_content_sha256"])==64

def test_p9_dev_001_cannot_enter_reference_registry():
    registry=ResearchRegistry.load(ROOT/"artifacts/model_registry/mlops_research_registry.yaml")
    invalid=next(x for x in registry.entries if x["registry_id"]=="AUDIT-P9-DEV-001-SKLEARN-MLP")
    assert invalid["registry_state"]=="INVALIDATED" and invalid["research_role"]=="AUDIT_ONLY"
    invalid={**invalid,"registry_id":"bad","registry_state":"REGISTERED_REFERENCE","research_role":"REFERENCE"}
    with pytest.raises(RegistrationError): ResearchRegistry().register(invalid,expected_model_fingerprint=invalid["model_spec_fingerprint"])
