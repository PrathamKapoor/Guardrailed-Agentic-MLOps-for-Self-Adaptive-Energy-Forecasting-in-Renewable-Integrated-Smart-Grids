#!/usr/bin/env python3
"""Governance Lifecycle Evaluation and Policy Ablation Study.

1. Governance Evaluation:
   Demonstrates DENY, REQUIRE_APPROVAL, and genuine ALLOW outcomes under the authoritative 13-gate engine.
2. Governance Ablation Study:
   Evaluates "Which governance controls actually matter?" across 7 policy ablations on a 100-candidate test pool.
   Measures: Admitted invalid candidates, admitted benchmark losers, and safety violations.
"""
from __future__ import annotations

import csv
import json
import logging
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from smartgrid_mlops.governance.policies import GovernancePolicy
from smartgrid_mlops.governance.policy_engine import GovernanceEngine
from smartgrid_mlops.governance.schemas import CandidateContext, TransitionRequest

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    stream=sys.stderr,
)
LOGGER = logging.getLogger("governance_ablation")


def run_evaluation_and_ablation():
    policy = GovernancePolicy.load(ROOT / "config/governance/phase_13_policy.yaml")
    engine = GovernanceEngine(policy)

    # -------------------------------------------------------------------------
    # Part 1: Explicit Outcomes Demonstration (DENY, REQUIRE_APPROVAL, ALLOW)
    # -------------------------------------------------------------------------
    LOGGER.info("Evaluating canonical governance outcome cases...")
    test_cases = [
        {
            "id": "CASE_01_GENUINE_ALLOW",
            "name": "Fully compliant challenger with valid simulation approval",
            "ctx": CandidateContext(
                subject_id="CANDIDATE-01",
                evidence_status="VALID",
                lineage_status="COMPLETE",
                actual_model_fingerprint="fp:model:valid",
                expected_model_fingerprint="fp:model:valid",
                actual_feature_fingerprint="fp:feat:valid",
                expected_feature_fingerprint="fp:feat:valid",
                protocol_hash=policy.document["accepted_protocol_hashes"][0],
                reproducibility_metadata="COMPLETE",
                deviation_status="RESOLVED",
                benchmark_gate="BENCHMARK_GATE_PASS",
                statistical_evidence="REQUIRED_PASS",
                approval_state="APPROVED",
                approval_actor="SIMULATION_POLICY",
                policy_mode="SIMULATION",
                evidence_refs=["artifacts/mlops/evidence/c01.json"],
            ),
            "req": TransitionRequest(
                subject_id="CANDIDATE-01",
                current_state="APPROVAL_PENDING",
                proposed_state="APPROVED_FOR_CANARY",
                actor_type="SIMULATION_POLICY",
                simulation=True,
            ),
            "expected_decision": "ALLOW",
        },
        {
            "id": "CASE_02_REQUIRE_APPROVAL",
            "name": "Challenger passes development gates, needs explicit human/sim approval",
            "ctx": CandidateContext(
                subject_id="CANDIDATE-02",
                evidence_status="VALID",
                lineage_status="COMPLETE",
                actual_model_fingerprint="fp:model:valid",
                expected_model_fingerprint="fp:model:valid",
                actual_feature_fingerprint="fp:feat:valid",
                expected_feature_fingerprint="fp:feat:valid",
                protocol_hash=policy.document["accepted_protocol_hashes"][0],
                reproducibility_metadata="COMPLETE",
                deviation_status="RESOLVED",
                benchmark_gate="BENCHMARK_GATE_PASS",
                statistical_evidence="REQUIRED_PASS",
                approval_state="NOT_REQUIRED",
                policy_mode="SIMULATION",
                evidence_refs=["artifacts/mlops/evidence/c02.json"],
            ),
            "req": TransitionRequest(
                subject_id="CANDIDATE-02",
                current_state="PROMOTION_ELIGIBLE",
                proposed_state="APPROVAL_PENDING",
                actor_type="SYSTEM",
                simulation=True,
            ),
            "expected_decision": "REQUIRE_APPROVAL",
        },
        {
            "id": "CASE_03_DENY_BENCHMARK_FAIL",
            "name": "Challenger with superior internal metric that loses to external baseline",
            "ctx": CandidateContext(
                subject_id="CANDIDATE-03",
                evidence_status="VALID",
                lineage_status="COMPLETE",
                actual_model_fingerprint="fp:model:valid",
                expected_model_fingerprint="fp:model:valid",
                actual_feature_fingerprint="fp:feat:valid",
                expected_feature_fingerprint="fp:feat:valid",
                protocol_hash=policy.document["accepted_protocol_hashes"][0],
                reproducibility_metadata="COMPLETE",
                deviation_status="RESOLVED",
                benchmark_gate="BENCHMARK_GATE_FAIL",  # LOSES BENCHMARK!
                statistical_evidence="REQUIRED_PASS",
                approval_state="NOT_REQUIRED",
                policy_mode="SIMULATION",
            ),
            "req": TransitionRequest(
                subject_id="CANDIDATE-03",
                current_state="REGISTERED_CHALLENGER",
                proposed_state="PROMOTION_ELIGIBLE",
                actor_type="SYSTEM",
                simulation=True,
            ),
            "expected_decision": "DENY",
        },
        {
            "id": "CASE_04_DENY_LINEAGE_INCOMPLETE",
            "name": "Challenger with missing training data provenance / lineage",
            "ctx": CandidateContext(
                subject_id="CANDIDATE-04",
                evidence_status="VALID",
                lineage_status="INCOMPLETE",  # BROKEN LINEAGE!
                actual_model_fingerprint="fp:model:valid",
                expected_model_fingerprint="fp:model:valid",
                actual_feature_fingerprint="fp:feat:valid",
                expected_feature_fingerprint="fp:feat:valid",
                protocol_hash=policy.document["accepted_protocol_hashes"][0],
                reproducibility_metadata="COMPLETE",
                deviation_status="RESOLVED",
                benchmark_gate="BENCHMARK_GATE_PASS",
                statistical_evidence="REQUIRED_PASS",
            ),
            "req": TransitionRequest(
                subject_id="CANDIDATE-04",
                current_state="REGISTERED_CHALLENGER",
                proposed_state="PROMOTION_ELIGIBLE",
            ),
            "expected_decision": "DENY",
        },
        {
            "id": "CASE_05_DENY_FINGERPRINT_MISMATCH",
            "name": "Challenger whose trained weights differ from frozen specification",
            "ctx": CandidateContext(
                subject_id="CANDIDATE-05",
                evidence_status="VALID",
                lineage_status="COMPLETE",
                actual_model_fingerprint="fp:model:tampered",  # MISMATCH!
                expected_model_fingerprint="fp:model:valid",
                actual_feature_fingerprint="fp:feat:valid",
                expected_feature_fingerprint="fp:feat:valid",
                protocol_hash=policy.document["accepted_protocol_hashes"][0],
                reproducibility_metadata="COMPLETE",
                deviation_status="RESOLVED",
                benchmark_gate="BENCHMARK_GATE_PASS",
                statistical_evidence="REQUIRED_PASS",
            ),
            "req": TransitionRequest(
                subject_id="CANDIDATE-05",
                current_state="REGISTERED_CHALLENGER",
                proposed_state="PROMOTION_ELIGIBLE",
            ),
            "expected_decision": "DENY",
        },
        {
            "id": "CASE_06_DENY_FINAL_TEST_VIOLATION",
            "name": "Challenger attempting unauthorized access to locked test partition",
            "ctx": CandidateContext(
                subject_id="CANDIDATE-06",
                requests_final_test_access=True,  # FORBIDDEN!
                evidence_status="VALID",
                lineage_status="COMPLETE",
                actual_model_fingerprint="fp:model:valid",
                expected_model_fingerprint="fp:model:valid",
                actual_feature_fingerprint="fp:feat:valid",
                expected_feature_fingerprint="fp:feat:valid",
                protocol_hash=policy.document["accepted_protocol_hashes"][0],
                reproducibility_metadata="COMPLETE",
                deviation_status="RESOLVED",
                benchmark_gate="BENCHMARK_GATE_PASS",
                statistical_evidence="REQUIRED_PASS",
            ),
            "req": TransitionRequest(
                subject_id="CANDIDATE-06",
                current_state="REGISTERED_CHALLENGER",
                proposed_state="PROMOTION_ELIGIBLE",
            ),
            "expected_decision": "DENY",
        }
    ]

    outcomes = []
    for tc in test_cases:
        dec = engine.evaluate(tc["ctx"], tc["req"])
        assert dec.decision == tc["expected_decision"], f"{tc['id']}: expected {tc['expected_decision']} got {dec.decision}"
        outcomes.append({
            "Case_ID": tc["id"],
            "Description": tc["name"],
            "Decision": dec.decision,
            "Failed_Gates": ";".join(dec.failed_gates) if dec.failed_gates else "NONE",
            "Reason_Codes": ";".join(dec.reason_codes),
            "Explanation": dec.explanation,
        })

    out_outcomes = ROOT / "artifacts/research_tables/governance_outcomes.csv"
    out_outcomes.parent.mkdir(parents=True, exist_ok=True)
    with out_outcomes.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(outcomes[0].keys()))
        w.writeheader()
        w.writerows(outcomes)
    LOGGER.info("Saved governance outcomes to %s", out_outcomes)

    # -------------------------------------------------------------------------
    # Part 2: Governance Policy Ablation Study (100-Candidate Pool)
    # -------------------------------------------------------------------------
    LOGGER.info("Running 7-policy Governance Ablation Study on 100-candidate pool...")
    np.random.seed(42)
    pool = []
    for i in range(100):
        # Defect injection probabilities:
        # 15% benchmark loser, 10% broken lineage, 10% fingerprint mismatch,
        # 8% invalid evidence/corrupt, 7% statistical fluke, 5% final-test violation
        is_bench_loser = np.random.rand() < 0.15
        is_lineage_broken = np.random.rand() < 0.10
        is_fp_mismatch = np.random.rand() < 0.10
        is_corrupt_evidence = np.random.rand() < 0.08
        is_stat_fluke = np.random.rand() < 0.07
        is_final_test_violation = np.random.rand() < 0.05
        
        is_flawed = (is_bench_loser or is_lineage_broken or is_fp_mismatch or 
                     is_corrupt_evidence or is_stat_fluke or is_final_test_violation)
        
        pool.append({
            "id": f"POOL-{i:03d}",
            "is_flawed": is_flawed,
            "bench_loser": is_bench_loser,
            "corrupt": is_corrupt_evidence,
            "lineage_broken": is_lineage_broken,
            "fp_mismatch": is_fp_mismatch,
            "ctx": CandidateContext(
                subject_id=f"POOL-{i:03d}",
                evidence_status="CORRUPTED" if is_corrupt_evidence else "VALID",
                lineage_status="INCOMPLETE" if is_lineage_broken else "COMPLETE",
                actual_model_fingerprint="fp:mismatch" if is_fp_mismatch else "fp:valid",
                expected_model_fingerprint="fp:valid",
                actual_feature_fingerprint="fp:feat:valid",
                expected_feature_fingerprint="fp:feat:valid",
                protocol_hash=policy.document["accepted_protocol_hashes"][0],
                reproducibility_metadata="COMPLETE",
                deviation_status="RESOLVED",
                benchmark_gate="BENCHMARK_GATE_FAIL" if is_bench_loser else "BENCHMARK_GATE_PASS",
                statistical_evidence="STATISTICAL_EVIDENCE_FAIL" if is_stat_fluke else "REQUIRED_PASS",
                approval_state="APPROVED",
                approval_actor="SIMULATION_POLICY",
                policy_mode="SIMULATION",
                requests_final_test_access=is_final_test_violation,
            ),
            "req": TransitionRequest(
                subject_id=f"POOL-{i:03d}",
                current_state="APPROVAL_PENDING",
                proposed_state="APPROVED_FOR_CANARY",
                actor_type="SIMULATION_POLICY",
                simulation=True,
            )
        })

    ablations = [
        ("FULL_13_GATE_POLICY", []),
        ("WITHOUT_BENCHMARK_GATE", ["BENCHMARK_GATE"]),
        ("WITHOUT_LINEAGE_GATE", ["LINEAGE_COMPLETENESS_GATE"]),
        ("WITHOUT_FINGERPRINT_GATES", ["MODEL_SPEC_FINGERPRINT_GATE", "FEATURE_SPEC_FINGERPRINT_GATE"]),
        ("WITHOUT_EVIDENCE_VALIDITY_GATE", ["EVIDENCE_VALIDITY_GATE"]),
        ("WITHOUT_STATISTICAL_GATE", ["STATISTICAL_EVIDENCE_GATE"]),
        ("WITHOUT_FINAL_TEST_GATE", ["FINAL_TEST_POLICY_GATE"]),
    ]

    ablation_results = []

    for ab_name, disabled_gates in ablations:
        admitted = 0
        rejected = 0
        admitted_flawed = 0
        admitted_bench_losers = 0
        admitted_corrupted = 0
        
        for cand in pool:
            dec = engine.evaluate(cand["ctx"], cand["req"])
            active_failed = [g for g in dec.failed_gates if g not in disabled_gates]
            
            is_admitted = len(active_failed) == 0
            if is_admitted:
                admitted += 1
                if cand["is_flawed"]:
                    admitted_flawed += 1
                if cand["bench_loser"]:
                    admitted_bench_losers += 1
                if cand["corrupt"]:
                    admitted_corrupted += 1
            else:
                rejected += 1

        ablation_results.append({
            "Policy_Configuration": ab_name,
            "Disabled_Gates": ";".join(disabled_gates) if disabled_gates else "NONE",
            "Candidates_Evaluated": len(pool),
            "Candidates_Admitted": admitted,
            "Candidates_Rejected": rejected,
            "Admitted_Flawed_Candidates": admitted_flawed,
            "Admitted_Benchmark_Losers": admitted_bench_losers,
            "Admitted_Corrupted_Models": admitted_corrupted,
            "Safety_Breach_Rate_Pct": round(100.0 * admitted_flawed / len(pool), 2),
        })

    out_ablation = ROOT / "artifacts/research_tables/governance_ablation_results.csv"
    with out_ablation.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(ablation_results[0].keys()))
        w.writeheader()
        w.writerows(ablation_results)
    LOGGER.info("Saved governance ablation results to %s", out_ablation)

    generate_figures(ablation_results)


def generate_figures(ablation_results: list[dict]):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig_dir = ROOT / "artifacts/research_figures"
    fig_dir.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(12, 6))

    configs = [r["Policy_Configuration"].replace("WITHOUT_", "NO_").replace("_GATE", "").replace("_GATES", "").replace("_POLICY", "") for r in ablation_results]
    flawed = [r["Admitted_Flawed_Candidates"] for r in ablation_results]
    bench_losers = [r["Admitted_Benchmark_Losers"] for r in ablation_results]
    corrupted = [r["Admitted_Corrupted_Models"] for r in ablation_results]

    x = np.arange(len(configs))
    w = 0.25

    ax.bar(x - w, flawed, w, label="Total Flawed Admitted (Safety Breaches)", color="#d62728")
    ax.bar(x, bench_losers, w, label="Benchmark Losers Admitted", color="#ff7f0e")
    ax.bar(x + w, corrupted, w, label="Corrupted Models Admitted", color="#9467bd")

    ax.set_xticks(x)
    ax.set_xticklabels(configs, rotation=25, ha="right", fontsize=9)
    ax.set_ylabel("Count per 100 Submissions", fontsize=10)
    ax.set_title("Governance Policy Ablation: Safety Breaches Admitted When Gates Are Removed", fontsize=12, fontweight="bold")
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend(frameon=True, fontsize=9)

    plt.tight_layout()
    plt.savefig(fig_dir / "governance_ablation.png", dpi=300, bbox_inches="tight")
    plt.savefig(fig_dir / "governance_ablation.svg", bbox_inches="tight")
    plt.close()
    LOGGER.info("Generated governance ablation figures.")


if __name__ == "__main__":
    run_evaluation_and_ablation()
