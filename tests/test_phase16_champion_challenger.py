from __future__ import annotations
import hashlib, json
from pathlib import Path

import pytest

from smartgrid_mlops.champion_challenger.canary import run_canary
from smartgrid_mlops.champion_challenger.comparison import comparison_record
from smartgrid_mlops.champion_challenger.evaluation import evaluate_challenger, load_phase15_contexts
from smartgrid_mlops.champion_challenger.events import AUDIT_EVENT_TYPES as CC_EVENTS
from smartgrid_mlops.champion_challenger.policy import PromotionPolicy
from smartgrid_mlops.champion_challenger.promotion import decide, is_unsafe_attempt
from smartgrid_mlops.champion_challenger.registry import ChampionRegistry
from smartgrid_mlops.champion_challenger.rollback import (degradation_detected, execute_rollback, preserve,
                                                          verify_restoration)
from smartgrid_mlops.champion_challenger.simulation import (EXPECTED_OUTCOMES, SCENARIO_IDS, run_pipeline,
                                                            scenario_context, valid_context)
from smartgrid_mlops.champion_challenger.validation import (assert_no_automatic_promotion, assert_no_final_test_access,
                                                            assert_no_forbidden_runner_flags)
from smartgrid_mlops.champion_challenger.schemas import ChallengerEvaluationContext
from smartgrid_mlops.models.serialization import save as save_model

ROOT = Path(__file__).parents[1]
POLICY = PromotionPolicy.load(ROOT / "config/governance/phase_16_promotion_policy.yaml")
BINDING = "eea37fc2029f422079e31d0299a561178eafd26e587957c5c9056a4dbcad00d5"
pytestmark = pytest.mark.filterwarnings("ignore:Setting the shape on a NumPy array:DeprecationWarning")


def evaluate(context, policy=POLICY):
    return decide(context, policy)


def test_policy_identity_and_freeze():
    assert POLICY.version == "16.0.0"
    assert POLICY.checksum == hashlib.sha256((ROOT / "config/governance/phase_16_promotion_policy.yaml").read_bytes()).hexdigest()
    assert POLICY.promotion_policy_fingerprint.startswith("promotion-policy-v1:sha256:")
    freeze = json.loads((ROOT / "artifacts/experimental_design/phase_16_champion_challenger_protocol_freeze.yaml").read_text())
    assert freeze["promotion_policy"]["policy_checksum"] == POLICY.checksum
    assert freeze["model_results_observed_when_frozen"] is False
    recorded = (ROOT / "artifacts/experimental_design/phase_16_champion_challenger_protocol_freeze.sha256").read_text().split()[0]
    assert hashlib.sha256((ROOT / "artifacts/experimental_design/phase_16_champion_challenger_protocol_freeze.yaml").read_bytes()).hexdigest() == recorded


def test_case5_all_gates_pass_approves():
    decision = evaluate(valid_context(protocol_hash=BINDING))
    assert decision.decision == "APPROVE" and decision.reason_codes == ["PROMOTION_APPROVED"]
    assert len(decision.gate_results) == 13
    assert all(g["passed"] for g in decision.gate_results)
    required = {"decision_id", "challenger_id", "reference_id", "metrics", "policy_version",
                "policy_checksum", "gate_results", "decision"}
    assert required <= decision.to_dict().keys()


def test_case1_better_mae_invalid_lineage_rejected():
    decision = evaluate(valid_context(protocol_hash=BINDING, lineage_status="INCOMPLETE"))
    assert decision.decision == "REJECT" and "LINEAGE_INCOMPLETE" in decision.reason_codes
    assert decision.metrics["challenger_mae"] < decision.metrics["reference_mae"]  # superior MAE is not enough


def test_case2_better_mae_benchmark_failure_rejected():
    decision = evaluate(valid_context(protocol_hash=BINDING, benchmark_gate="BENCHMARK_GATE_FAIL"))
    assert decision.decision == "REJECT" and "BENCHMARK_REQUIREMENT_NOT_SATISFIED" in decision.reason_codes


def test_case3_missing_metadata_rejected():
    decision = evaluate(valid_context(protocol_hash=BINDING, metadata_complete=False))
    assert decision.decision == "REJECT" and "METADATA_INCOMPLETE" in decision.reason_codes


def test_case4_invalid_fingerprint_rejected():
    decision = evaluate(valid_context(protocol_hash=BINDING, actual_model_fingerprint="tampered"))
    assert decision.decision == "REJECT" and "MODEL_FINGERPRINT_MISMATCH" in decision.reason_codes
    feature = evaluate(valid_context(protocol_hash=BINDING, actual_feature_fingerprint="tampered"))
    assert feature.decision == "REJECT" and "FEATURE_FINGERPRINT_MISMATCH" in feature.reason_codes


def test_worse_challenger_and_other_hard_gates_rejected():
    worse = evaluate(valid_context(protocol_hash=BINDING, challenger_mae=105.0))
    assert worse.decision == "REJECT" and "CHALLENGER_NOT_BETTER" in worse.reason_codes
    unregistered = evaluate(valid_context(protocol_hash=BINDING, registered=False))
    assert unregistered.decision == "REJECT" and "CHALLENGER_NOT_REGISTERED" in unregistered.reason_codes
    protocol = evaluate(valid_context(protocol_hash="unknown"))
    assert protocol.decision == "REJECT" and "PROTOCOL_MISMATCH" in protocol.reason_codes
    final_test = evaluate(valid_context(protocol_hash=BINDING, requests_final_test_access=True))
    assert final_test.decision == "REJECT" and "FINAL_TEST_POLICY_VIOLATION" in final_test.reason_codes
    incomplete_eval = evaluate(valid_context(protocol_hash=BINDING, evaluation_completed=False, matched_evaluation_rows=0))
    assert incomplete_eval.decision == "REJECT" and "EVALUATION_INCOMPLETE" in incomplete_eval.reason_codes
    statistical = evaluate(valid_context(protocol_hash=BINDING, statistical_evidence="REQUIRED_FAIL"))
    assert statistical.decision == "REJECT" and "STATISTICAL_EVIDENCE_INSUFFICIENT" in statistical.reason_codes


def test_approval_missing_defers_and_rejected_denies():
    pending = evaluate(valid_context(protocol_hash=BINDING, approval_state="PENDING"))
    assert pending.decision == "DEFER" and pending.reason_codes == ["APPROVAL_REQUIRED"]
    rejected = evaluate(valid_context(protocol_hash=BINDING, approval_state="REJECTED"))
    assert rejected.decision == "REJECT" and "APPROVAL_REJECTED" in rejected.reason_codes
    wrong_actor = evaluate(valid_context(protocol_hash=BINDING, approval_state="APPROVED",
                                         approval_actor="HUMAN_CLAIM_IN_SIMULATION"))
    assert wrong_actor.decision == "DEFER" and "APPROVAL_REQUIRED" in wrong_actor.reason_codes


def test_decision_content_deterministic_except_ids():
    a, b = evaluate(valid_context(protocol_hash=BINDING)), evaluate(valid_context(protocol_hash=BINDING))
    assert a.scientific_content() == b.scientific_content()
    assert a.decision_id != b.decision_id


def test_comparison_requires_matched_protocol():
    record = comparison_record(reference_metrics={"MAE": 100.0, "RMSE": 0, "sMAPE": 0, "nMAE": 0, "nRMSE": 0},
                               challenger_metrics={"MAE": 90.0, "RMSE": 0, "sMAPE": 0, "nMAE": 0, "nRMSE": 0},
                               matched_rows=336)
    assert record["relative_mae_improvement_percent"] == pytest.approx(10.0) and record["challenger_better"]
    with pytest.raises(ValueError):
        comparison_record(reference_metrics={"MAE": 1, "RMSE": 0, "sMAPE": 0, "nMAE": 0, "nRMSE": 0},
                          challenger_metrics={"MAE": 1, "RMSE": 0, "sMAPE": 0, "nMAE": 0, "nRMSE": 0},
                          matched_rows=10, same_feature_representation=False)
    with pytest.raises(ValueError):
        comparison_record(reference_metrics={"MAE": 1, "RMSE": 0, "sMAPE": 0, "nMAE": 0, "nRMSE": 0},
                          challenger_metrics={"MAE": 1, "RMSE": 0, "sMAPE": 0, "nMAE": 0, "nRMSE": 0},
                          matched_rows=0)


def test_canary_guardrail():
    passing = run_canary(valid_context(protocol_hash=BINDING, canary_regression_percent=-3.0), POLICY)
    assert passing.passed and passing.reason_code == "CANARY_PASSED"
    failing = run_canary(valid_context(protocol_hash=BINDING, canary_regression_percent=0.5), POLICY)
    assert not failing.passed and failing.reason_code == "CANARY_FAILED"


@pytest.fixture()
def preserved_reference(tmp_path):
    from sklearn.ensemble import RandomForestRegressor
    model = RandomForestRegressor(n_estimators=5, random_state=42)
    model.fit([[float(i)] * 3 for i in range(30)], [2.0 * i for i in range(30)])
    artifact = tmp_path / "reference.joblib"
    save_model(model, artifact)
    return preserve("MLOPS-REF-LOAD-H24-V1", role="REFERENCE", artifact_path=str(artifact),
                    model_spec_fingerprint="fp-true", lineage_node="spec:fp-true")


def test_rollback_success_and_restoration_verification(preserved_reference):
    context = valid_context(protocol_hash=BINDING, challenger_id="SIM-CC05", post_promotion_regression_percent=4.2)
    triggered, regression, threshold = degradation_detected(4.2, POLICY)
    assert triggered and regression == pytest.approx(4.2) and threshold == 0.0
    verification = verify_restoration(preserved_reference, expected_fingerprint="fp-true",
                                      lineage_nodes={"spec:fp-true"}, probe_features=[[1.0, 2.0, 3.0]] * 4)
    assert not verification["failed"]
    record = execute_rollback(promoted_model_id="SIM-CC05", previous=preserved_reference,
                              regression_percent=4.2, threshold_percent=0.0, verification=verification)
    assert record.outcome == "ROLLBACK_COMPLETED" and record.reason_code == "ROLLBACK_COMPLETED"
    assert not degradation_detected(0.0, POLICY)[0]


def test_rollback_integrity_failure_blocks(preserved_reference):
    corrupted = preserve(preserved_reference.model_id, role="REFERENCE",
                         artifact_path=preserved_reference.artifact_path,
                         model_spec_fingerprint="corrupted", lineage_node=preserved_reference.lineage_node)
    verification = verify_restoration(corrupted, expected_fingerprint="fp-true",
                                      lineage_nodes={"spec:fp-true"}, probe_features=[[1.0, 2.0, 3.0]] * 4)
    assert "fingerprint_matches" in verification["failed"]
    record = execute_rollback(promoted_model_id="SIM-CC06", previous=corrupted,
                              regression_percent=4.2, threshold_percent=0.0, verification=verification)
    assert record.outcome == "ROLLBACK_BLOCKED" and record.reason_code == "ROLLBACK_VERIFICATION_FAILED"
    missing = preserve("GONE", role="REFERENCE", artifact_path="does/not/exist.joblib",
                       model_spec_fingerprint="fp-true", lineage_node="spec:fp-true")
    missing_verification = verify_restoration(missing, expected_fingerprint="fp-true", lineage_nodes=set())
    assert "artifact_exists" in missing_verification["failed"] and "lineage_exists" in missing_verification["failed"]


def test_canary_failure_prevents_activation(preserved_reference):
    context = valid_context(protocol_hash=BINDING, challenger_id="SIM-CANARY-FAIL", canary_regression_percent=2.0)
    result = run_pipeline(context, POLICY, preservation=preserved_reference,
                          lineage_nodes={"spec:fp-true"}, probe_features=[[1.0, 2.0, 3.0]] * 4,
                          expected_preservation_fingerprint="fp-true")
    assert result["decision"] == "APPROVE" and not result["promoted"]
    assert result["outcome"] == "CANARY_FAILED_ROLLED_BACK"


def test_no_automatic_promotion_invariant():
    context = valid_context(protocol_hash=BINDING)  # superior MAE challenger
    rejected = evaluate(valid_context(protocol_hash=BINDING, lineage_status="INCOMPLETE"))
    with pytest.raises(ValueError):
        assert_no_automatic_promotion(rejected, None, promoted=True)
    assert_no_automatic_promotion(rejected, None, promoted=False)
    decision = evaluate(context)
    canary = run_canary(context, POLICY)
    assert_no_automatic_promotion(decision, canary, promoted=True)  # only governed path may promote


def test_all_frozen_scenarios_match_expected_outcomes(preserved_reference):
    corrupted = preserve(preserved_reference.model_id, role="REFERENCE",
                         artifact_path=preserved_reference.artifact_path,
                         model_spec_fingerprint="corrupted", lineage_node=preserved_reference.lineage_node)
    for scenario_id in SCENARIO_IDS:
        context = scenario_context(scenario_id, protocol_hash=BINDING)
        result = run_pipeline(context, POLICY, preservation=preserved_reference,
                              corrupted_preservation=corrupted if scenario_id == "CC06" else None,
                              lineage_nodes={"spec:fp-true"}, probe_features=[[1.0, 2.0, 3.0]] * 4,
                              expected_preservation_fingerprint="fp-true")
        assert result["outcome"] == EXPECTED_OUTCOMES[scenario_id], scenario_id
        unsafe = is_unsafe_attempt(context, decide(context, POLICY))
        if scenario_id in {"CC02", "CC03"}:
            assert unsafe  # superior-MAE challengers blocked by governance


def test_real_phase15_challengers_all_rejected_for_promotion():
    import sys
    sys.path.insert(0, str(ROOT / "scripts"))
    from run_champion_challenger_simulation import expected_fingerprints
    fingerprints = expected_fingerprints()
    contexts = load_phase15_contexts(ROOT, protocol_hash=BINDING)
    assert len(contexts) == 18
    unsafe_blocked = 0
    unsafe_total = 0
    for context in contexts:
        from dataclasses import replace
        context = replace(context, expected_model_fingerprint=fingerprints[context.target])
        decision = evaluate(context)
        assert decision.decision == "REJECT", context.challenger_id
        if "CHALLENGER_NOT_BETTER" in decision.reason_codes:
            assert context.challenger_mae >= context.reference_mae
        else:
            assert "BENCHMARK_REQUIREMENT_NOT_SATISFIED" in decision.reason_codes
        if is_unsafe_attempt(context, decision):
            unsafe_total += 1; unsafe_blocked += 1
    assert unsafe_total == 14 and unsafe_blocked == 14  # superior-MAE synthetic challengers, all blocked


def test_champion_registry_additive_and_restoration_state(tmp_path):
    registry = ChampionRegistry()
    registry.record_preservation(preserve("REF", role="REFERENCE", artifact_path="a.joblib",
                                          model_spec_fingerprint="fp", lineage_node="n").to_dict())
    registry.record_promotion({"challenger_id": "CHAL", "reference_id": "REF", "scenario": "CC01",
                               "state": "ACTIVE (SIMULATION)", "simulation": True})
    registry.record_rollback({"promoted_model_id": "CHAL", "previous_model_id": "REF", "scenario": "CC05",
                              "outcome": "ROLLBACK_COMPLETED", "simulation": True})
    registry.dump(tmp_path / "champions.yaml")
    reloaded = ChampionRegistry.load(tmp_path / "champions.yaml")
    assert reloaded.active_models["CC05"]["challenger_id"] == "REF" and reloaded.active_models["CC05"]["restored"]
    assert reloaded.active_models["CC01"]["challenger_id"] == "CHAL"
    # Phase 13 lifecycle registry and Phase 15 challenger registry are untouched
    lifecycle = json.loads((ROOT / "artifacts/model_registry/lifecycle_registry.yaml").read_text())
    references = [e for e in lifecycle["entries"] if e["research_role"] == "REFERENCE"]
    assert len(references) == 3 and all(e["lifecycle_state"] == "REGISTERED_REFERENCE" for e in references)
    phase15 = json.loads((ROOT / "artifacts/model_registry/phase_15_challengers.yaml").read_text())
    assert all(e["registry_state"] == "REGISTERED_CHALLENGER" and e["promotion_eligible"] is False
               for e in phase15["entries"])


def test_final_test_and_runner_flags_and_audit_types():
    for bad in ("final_test/targets.parquet", "november/labels.csv", "december-eval"):
        with pytest.raises(ValueError):
            assert_no_final_test_access(bad)
    source = (ROOT / "scripts/run_champion_challenger_simulation.py").read_text(encoding="utf-8")
    assert_no_forbidden_runner_flags(source)
    assert "MODEL_PROMOTED" in CC_EVENTS
    retraining_source = (ROOT / "src/smartgrid_mlops/retraining/events.py").read_text(encoding="utf-8")
    assert "MODEL_PROMOTED" not in retraining_source  # retraining still cannot emit promotions
    assert set() <= {"CHALLENGER_EVALUATED", "PROMOTION_REQUESTED", "PROMOTION_APPROVED",
                     "PROMOTION_REJECTED", "CANARY_STARTED", "CANARY_FAILED", "MODEL_PROMOTED",
                     "ROLLBACK_REQUESTED", "ROLLBACK_COMPLETED"} - set(CC_EVENTS)


def test_mlflow_native_champion_challenger_contract(tmp_path):
    import mlflow
    from smartgrid_mlops.mlops.tracking import TrackingConfig, tracked_run
    cfg = TrackingConfig(tmp_path)
    context = valid_context(protocol_hash=BINDING)
    decision = evaluate(context)
    with tracked_run(cfg, "phase16/champion_challenger", tags={
            "tracking_origin": "NATIVE_MLFLOW", "research_phase": "16",
            "experiment_type": "CHAMPION_CHALLENGER", "reference_id": context.reference_id,
            "challenger_id": context.challenger_id, "promotion_decision": decision.decision,
            "promotion_policy_fingerprint": POLICY.promotion_policy_fingerprint,
            "simulation": "true"}) as run:
        mlflow.log_metric("relative_mae_improvement_percent", 10.0)
        run_id = run.info.run_id
    client = cfg.initialize()
    fetched = client.get_run(run_id)
    assert fetched.data.tags["research_phase"] == "16"
    assert fetched.data.tags["experiment_type"] == "CHAMPION_CHALLENGER"
    assert fetched.data.tags["promotion_decision"] == "APPROVE"
    assert fetched.data.tags["final_test_training_access"] == "NO"
    assert fetched.data.metrics["relative_mae_improvement_percent"] == pytest.approx(10.0)


def test_official_simulation_summary_contract_when_present():
    path = ROOT / "artifacts/champion_challenger/phase_16/manifests/simulation_summary.json"
    if not path.exists():
        pytest.skip("official run not executed yet")
    summary = json.loads(path.read_text())
    assert summary["automatic_promotions"] == 0
    assert summary["unsafe_promotion_attempts"] == summary["blocked_unsafe_promotions"]
    assert summary["scenario_governance_accuracy_percent"] == 100.0
