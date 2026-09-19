#!/usr/bin/env python3
"""Phase 16 champion-challenger simulation runner; no final-test option, no HPO flags, no deployment."""
from __future__ import annotations
import argparse, hashlib, json, sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import mlflow
from smartgrid_mlops.champion_challenger.evaluation import evaluate_challenger, load_phase15_contexts
from smartgrid_mlops.champion_challenger.events import emit
from smartgrid_mlops.champion_challenger.policy import PromotionPolicy
from smartgrid_mlops.champion_challenger.promotion import decide, is_unsafe_attempt
from smartgrid_mlops.champion_challenger.registry import ChampionRegistry
from smartgrid_mlops.champion_challenger.rollback import preserve
from smartgrid_mlops.champion_challenger.simulation import (EXPECTED_OUTCOMES, SCENARIO_IDS,
                                                            run_pipeline, scenario_context)
from smartgrid_mlops.champion_challenger.schemas import PreservationRecord
from smartgrid_mlops.mlops.lineage import LineageGraph
from smartgrid_mlops.mlops.tracking import TrackingConfig, tracked_run
from smartgrid_mlops.models.serialization import save as save_model
from smartgrid_mlops.retraining.dataset import build_view, load_feature_rows, load_hourly_series
from smartgrid_mlops.retraining.refit import fit_rows, load_reference_spec
import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stderr,
)
LOGGER = logging.getLogger(__name__)

OUT = ROOT / "artifacts/champion_challenger/phase_16"
AUDIT = ROOT / "artifacts/mlops/audit/events.jsonl"
CHAMPION_REGISTRY = ROOT / "artifacts/model_registry/phase_16_champion_registry.yaml"
PROTOCOL_BINDING_HASH = "eea37fc2029f422079e31d0299a561178eafd26e587957c5c9056a4dbcad00d5"
ONSET = datetime(2020, 8, 1)
TARGETS = ("load", "wind", "pv")


def sha(path: Path) -> str: return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def append_jsonl(path: Path, records) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True) + "\n")


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists(): return []
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def expected_fingerprints() -> dict[str, str]:
    from run_governed_retraining import expected_model_fingerprint
    return {t: expected_model_fingerprint(t) for t in TARGETS}


def preserve_reference_models(fingerprints: dict[str, str]) -> dict[str, PreservationRecord]:
    """Fit each frozen reference specification on its pre-onset window (identical to
    the Phase 15 REFERENCE_INFERENCE reconstruction) and preserve the artifacts so
    rollback restoration can be verified against real, loadable models."""
    records = {}
    for target in TARGETS:
        timestamps, values = load_hourly_series(ROOT, target)
        rows = load_feature_rows(ROOT, target)
        view = build_view(rows, timestamps, values)
        spec = load_reference_spec(ROOT, target)
        model, _ = fit_rows([r for r in view if r["target_timestamp"] < ONSET],
                            model_family=spec["model_family"], hyperparameters=spec["hyperparameters"], seed=42)
        artifact = OUT / f"models/reference_{target}_pre_onset.joblib"
        save_model(model, artifact)
        records[target] = preserve(
            f"MLOPS-REF-{target.upper()}-H24-V1", role="REFERENCE",
            artifact_path=str(artifact), model_spec_fingerprint=fingerprints[target],
            lineage_node=f"model-spec:{fingerprints[target]}")
    return records


def lineage_nodes() -> set[str]:
    graph_path = ROOT / "artifacts/retraining/phase_15/manifests/challenger_lineage.yaml"
    graph = LineageGraph.load(graph_path) if graph_path.exists() else LineageGraph()
    return set(graph.nodes)


def audit_emitter():
    def _emit(event_type: str, subject_id: str, details: dict):
        emit(AUDIT, event_type, subject_id, details)
    return _emit


def log_mlflow(policy: PromotionPolicy, *, reference_id: str, challenger_id: str, target: str,
               decision: str, metrics: dict, scenario_label: str) -> str:
    with tracked_run(TrackingConfig(ROOT), "phase16/champion_challenger", tags={
            "tracking_origin": "NATIVE_MLFLOW", "research_phase": "16",
            "experiment_type": "CHAMPION_CHALLENGER", "reference_id": reference_id,
            "challenger_id": challenger_id, "target": target, "promotion_decision": decision,
            "promotion_policy_fingerprint": policy.promotion_policy_fingerprint,
            "policy_version": policy.version, "simulation": "true",
            "scenario_label": scenario_label, "evidence_status": "VALID"}, params={
            "reference_id": reference_id, "challenger_id": challenger_id, "target": target,
            "policy_checksum": policy.checksum}) as run:
        mlflow.log_metrics({k: float(v) for k, v in metrics.items()})
        return run.info.run_id


def run_real_challenger_batch(policy: PromotionPolicy, fingerprints: dict[str, str]) -> list[dict]:
    contexts = load_phase15_contexts(ROOT, protocol_hash=PROTOCOL_BINDING_HASH)
    results = []
    emit_fn = audit_emitter()
    for context in contexts:
        context = replace_expected(context, fingerprints[context.target])
        decision = decide(context, policy)
        evaluation = evaluate_challenger(context)
        emit_fn("CHALLENGER_EVALUATED", context.challenger_id,
                {"reference_id": context.reference_id, "target": context.target,
                 "challenger_mae": context.challenger_mae, "reference_mae": context.reference_mae,
                 "real_phase15_challenger": True})
        emit_fn("PROMOTION_REQUESTED", context.challenger_id, {"reference_id": context.reference_id})
        event = {"APPROVE": "PROMOTION_APPROVED", "REJECT": "PROMOTION_REJECTED",
                 "DEFER": "PROMOTION_DEFERRED"}[decision.decision]
        emit_fn(event, context.challenger_id, {"reason_codes": decision.reason_codes})
        run_id = log_mlflow(policy, reference_id=context.reference_id, challenger_id=context.challenger_id,
                            target=context.target, decision=decision.decision,
                            metrics={"reference_mae": context.reference_mae,
                                     "challenger_mae": context.challenger_mae,
                                     "relative_mae_improvement_percent": decision.metrics["relative_mae_improvement_percent"]},
                            scenario_label="REAL_PHASE15_CHALLENGER")
        results.append({"challenger_id": context.challenger_id, "reference_id": context.reference_id,
                        "target": context.target, "decision": decision.decision,
                        "reason_codes": decision.reason_codes,
                        "relative_mae_improvement_percent": decision.metrics["relative_mae_improvement_percent"],
                        "unsafe_attempt": is_unsafe_attempt(context, decision),
                        "blocked": is_unsafe_attempt(context, decision) and decision.decision != "APPROVE",
                        "mlflow_run_id": run_id, "decision_record": decision.to_dict(),
                        "evaluation": evaluation})
    return results


def replace_expected(context, expected_model_fingerprint: str):
    from dataclasses import replace
    return replace(context, expected_model_fingerprint=expected_model_fingerprint)


def run_scenarios(policy: PromotionPolicy, preservation: dict[str, PreservationRecord],
                  nodes: set[str]) -> list[dict]:
    emit_fn = audit_emitter()
    probe = [[1.0, 2.0, 3.0]] * 4
    registry = ChampionRegistry.load(CHAMPION_REGISTRY)
    results = []
    for scenario_id in SCENARIO_IDS:
        context = scenario_context(scenario_id, protocol_hash=PROTOCOL_BINDING_HASH)
        rollback_previous = preservation["load"]
        corrupted = PreservationRecord(
            model_id=rollback_previous.model_id, role=rollback_previous.role,
            artifact_path=rollback_previous.artifact_path,
            model_spec_fingerprint="corrupted-fingerprint",
            lineage_node=rollback_previous.lineage_node)
        result = run_pipeline(
            context, policy, preservation=rollback_previous,
            corrupted_preservation=corrupted if scenario_id == "CC06" else None,
            lineage_nodes=nodes, probe_features=probe, emit_event=emit_fn,
            expected_preservation_fingerprint=rollback_previous.model_spec_fingerprint)
        result["scenario_id"] = scenario_id
        result["expected_outcome"] = EXPECTED_OUTCOMES[scenario_id]
        result["correct"] = result["outcome"] == EXPECTED_OUTCOMES[scenario_id]
        run_id = log_mlflow(policy, reference_id=context.reference_id, challenger_id=context.challenger_id,
                            target=context.target, decision=result["decision"],
                            metrics={"reference_mae": context.reference_mae,
                                     "challenger_mae": context.challenger_mae,
                                     "relative_mae_improvement_percent": result["evaluation"]["relative_mae_improvement_percent"],
                                     "canary_regression_percent": context.canary_regression_percent},
                            scenario_label=scenario_id)
        result["mlflow_run_id"] = run_id
        if result["promoted"]:
            registry.record_promotion({"challenger_id": context.challenger_id,
                                       "reference_id": context.reference_id, "scenario": scenario_id,
                                       "state": "ACTIVE (SIMULATION)", "canary": result["canary"],
                                       "policy_fingerprint": policy.promotion_policy_fingerprint,
                                       "simulation": True})
        if result["rollback"] is not None:
            registry.record_rollback({"promoted_model_id": context.challenger_id,
                                      "previous_model_id": result["rollback"]["previous_model_id"],
                                      "scenario": scenario_id, "outcome": result["rollback"]["outcome"],
                                      "verification": result["rollback"]["verification"], "simulation": True})
        results.append(result)
    registry.dump(CHAMPION_REGISTRY)
    return results


def summary(real_results: list[dict], scenario_results: list[dict]) -> dict:
    all_decisions = [r["decision"] for r in real_results] + [r["decision"] for r in scenario_results]
    unsafe = [r for r in real_results + scenario_results if r.get("unsafe_attempt")]
    rollbacks = [r for r in scenario_results if r.get("rollback")]
    correct = sum(1 for r in scenario_results if r["correct"])
    return {
        "promotion_attempts": len(all_decisions),
        "approved": all_decisions.count("APPROVE"), "rejected": all_decisions.count("REJECT"),
        "deferred": all_decisions.count("DEFER"),
        "unsafe_promotion_attempts": len(unsafe),
        "blocked_unsafe_promotions": sum(1 for r in unsafe if r["decision"] != "APPROVE"),
        "unsafe_promotion_prevention_rate_percent": 100.0 * sum(1 for r in unsafe if r["decision"] != "APPROVE") / len(unsafe) if unsafe else None,
        "rollback_attempts": len(rollbacks),
        "successful_rollback": sum(1 for r in rollbacks if r["rollback"]["outcome"] == "ROLLBACK_COMPLETED"),
        "failed_rollback": sum(1 for r in rollbacks if r["rollback"]["outcome"] == "ROLLBACK_BLOCKED"),
        "scenario_governance_accuracy_percent": 100.0 * correct / len(scenario_results) if scenario_results else None,
        "automatic_promotions": 0,
        "real_challengers_evaluated": len(real_results),
    }


def main():
    parser = argparse.ArgumentParser(description="Phase 16 champion-challenger governance simulation (deterministic, no agents)")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--scenario", choices=SCENARIO_IDS)
    parser.add_argument("--evaluate-real", action="store_true")
    args = parser.parse_args()
    if not (args.all or args.scenario or args.evaluate_real):
        parser.error("select --all, --scenario <CCxx>, or --evaluate-real")
    policy = PromotionPolicy.load(ROOT / "config/governance/phase_16_promotion_policy.yaml")
    fingerprints = expected_fingerprints()
    real_results: list[dict] = []
    scenario_results: list[dict] = []
    if args.evaluate_real or args.all:
        real_results = run_real_challenger_batch(policy, fingerprints)
        dump(OUT / "evaluations/real_phase15_challengers.json",
             {"policy_checksum": policy.checksum, "results": real_results})
    if args.scenario or args.all:
        preservation = preserve_reference_models(fingerprints)
        registry = ChampionRegistry.load(CHAMPION_REGISTRY)
        for record in preservation.values():
            registry.record_preservation(record.to_dict())
        registry.dump(CHAMPION_REGISTRY)
        if args.scenario:
            nodes = lineage_nodes()
            results = run_scenarios(policy, preservation, nodes)
            scenario_results = [r for r in results if r["scenario_id"] == args.scenario]
        else:
            scenario_results = run_scenarios(policy, preservation, lineage_nodes())
        dump(OUT / "scenario_results/cc_scenarios.json",
             {"policy_checksum": policy.checksum, "results": scenario_results})
    metrics = summary(real_results, scenario_results)
    dump(OUT / "manifests/simulation_summary.json", metrics)
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
