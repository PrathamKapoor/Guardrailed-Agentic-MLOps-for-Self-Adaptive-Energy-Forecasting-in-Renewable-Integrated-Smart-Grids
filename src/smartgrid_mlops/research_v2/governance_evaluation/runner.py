"""Stage 12: orchestrator that runs every Stage 10 candidate through
the existing deterministic governance engine.

This module is the single entry point that:
  1. Loads the frozen Phase 13 governance policy.
  2. Reads every Stage 10 evidence package.
  3. Reads the Stage 11 per-fold summary.
  4. Normalizes the evidence for each candidate.
  5. Builds the existing `CandidateContext` + `TransitionRequest`
     for each candidate.
  6. Calls the existing `GovernanceEngine.evaluate(...)` once per
     candidate.
  7. Records the resulting `GovernanceDecision` to the existing
     append-only audit JSONL (the only allowed mutation).
  8. Writes:
     - `artifacts/v2/governance_evaluation/normalized_evidence.json`
     - `artifacts/v2/governance_evaluation/candidate_evaluations.json`
     - `artifacts/v2/governance_evaluation/evidence_gaps.json`
     - `artifacts/v2/governance_evaluation/stage12_summary.json`
     - `artifacts/v2/governance_evaluation/stage12_audit.jsonl`
     - `artifacts/v2/governance_evaluation/registry_state.json`
"""
from __future__ import annotations
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from smartgrid_mlops.governance.policies import GovernancePolicy

from .adapter import DEFAULT_AUDIT_PATH, evaluate_candidate
from .evidence import (
    normalize_evidence,
    read_stage_10_evidence, read_stage_11_per_fold, read_stage_11_summary,
)


V2_ROOT = Path(__file__).resolve().parents[4] / "artifacts" / "v2" / "governance_evaluation"
STAGE_10_DIR = Path(__file__).resolve().parents[4] / "artifacts" / "v2" / "residual_forecasting" / "evidence_packages"
STAGE_11_PER_FOLD = Path(__file__).resolve().parents[4] / "artifacts" / "v2" / "research_validation" / "fold_results"
STAGE_11_SUMMARY = Path(__file__).resolve().parents[4] / "artifacts" / "v2" / "research_validation" / "fold_results" / "per_fold_summary.json"
PHASE_13_POLICY = Path(__file__).resolve().parents[4] / "config" / "governance" / "phase_13_policy.yaml"


def _candidate_to_record(record: dict) -> dict:
    return {k: v for k, v in record.items()
            if k not in ("evidence_classification",)}


def _registry_state_paths() -> dict:
    return {
        "model_registry_lifecycle": Path(__file__).resolve().parents[4]
            / "artifacts" / "model_registry" / "lifecycle_registry.yaml",
        "model_registry_research": Path(__file__).resolve().parents[4]
            / "artifacts" / "model_registry" / "mlops_research_registry.yaml",
        "phase_19_protocol_freeze": Path(__file__).resolve().parents[4]
            / "artifacts" / "experimental_design" / "phase_19_final_evaluation_protocol_freeze.yaml",
        "phase_13_policy": PHASE_13_POLICY,
        "agent_firewall": Path(__file__).resolve().parents[4]
            / "src" / "smartgrid_mlops" / "agents" / "firewall.py",
        "governance_engine": Path(__file__).resolve().parents[4]
            / "src" / "smartgrid_mlops" / "governance" / "policy_engine.py",
    }


def _hash_paths(paths: dict) -> dict:
    out = {}
    for k, p in paths.items():
        if p.is_file():
            out[k] = hashlib.sha256(p.read_bytes()).hexdigest()
        else:
            out[k] = None
    return out


def run_governance_evaluation(
    *,
    policy_path: Path = PHASE_13_POLICY,
    stage_10_dir: Path = STAGE_10_DIR,
    stage_11_per_fold: Path = STAGE_11_PER_FOLD,
    stage_11_summary: Path = STAGE_11_SUMMARY,
    out_dir: Path = V2_ROOT,
    audit_path: Path = DEFAULT_AUDIT_PATH,
    proposed_transition: str = "EXPERIMENTAL -> VALIDATED",
) -> dict:
    """Run the full Stage 12 evaluation. The ONLY mutation is
    the append to `audit_path`. The only files written are inside
    `out_dir` (under `artifacts/v2/governance_evaluation/`)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    audit_path.parent.mkdir(parents=True, exist_ok=True)

    v1_paths = _registry_state_paths()
    hashes_before = _hash_paths(v1_paths)

    policy = GovernancePolicy.load(policy_path)
    s10_evidence_list = read_stage_10_evidence(stage_10_dir)
    s11_per_fold_list = read_stage_11_per_fold(stage_11_per_fold)
    s11_summary = read_stage_11_summary(stage_11_summary)

    candidate_records: list[dict] = []
    normalized_records: list[dict] = []
    for s10 in s10_evidence_list:
        ev = normalize_evidence(
            s10, s11_per_fold_list, s11_summary,
            proposed_transition=proposed_transition,
        )
        record = evaluate_candidate(
            ev,
            policy=policy,
            audit_path=audit_path,
        )
        candidate_records.append(_candidate_to_record(record))
        normalized_records.append({
            "candidate_id": ev.candidate_id,
            "target": ev.target,
            "proposed_transition": ev.proposed_transition,
            "chronology_folds": ev.chronology_folds,
            "evidence_classification": [
                {"name": c.name, "kind": c.kind, "value": c.value,
                 "where": c.where, "note": c.note}
                for c in ev.classification
            ],
        })

    evidence_gaps = {
        "schema": "stage_12_evidence_gaps_v1",
        "missing_evidence_per_candidate": [
            {"candidate_id": r["subject_id"],
             "missing": [g["name"] for g in r["missing_evidence"]],
             "negative": [g["name"] for g in r["negative_evidence"]],
             "context_dependent": [g["name"] for g in r["context_dependent_evidence"]]}
            for r in candidate_records
        ],
        "missing_evidence_intersection": sorted({
            g["name"]
            for r in candidate_records
            for g in r["missing_evidence"]
        }),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    decisions = [r["decision"] for r in candidate_records]
    decisions_count = {d: decisions.count(d) for d in set(decisions)}
    summary = {
        "schema": "stage_12_summary_v1",
        "stage": "12",
        "evaluation_purpose": (
            "Translate Stage 10 and Stage 11 research evidence into "
            "Phase 13 governance requests and record the resulting "
            "deterministic decision. Stage 12 does NOT promote, deploy, "
            "or otherwise mutate any lifecycle state."),
        "policy_id": policy.policy_id,
        "policy_version": policy.version,
        "policy_checksum": policy.checksum,
        "governance_policy_fingerprint": policy.governance_policy_fingerprint,
        "n_candidates_evaluated": len(candidate_records),
        "decision_counts": decisions_count,
        "candidate_decisions": [
            {"candidate_id": r["subject_id"], "target": r["target"],
             "decision": r["decision"],
             "reason_codes": r["reason_codes"]}
            for r in candidate_records
        ],
        "lifecycle_mutated": False,
        "registration_state_changed": False,
        "champion_state_changed": False,
        "policy_changed": False,
        "audit_path": str(audit_path.relative_to(out_dir.parent.parent)),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    (out_dir / "normalized_evidence.json").write_text(
        json.dumps(normalized_records, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    (out_dir / "candidate_evaluations.json").write_text(
        json.dumps(candidate_records, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    (out_dir / "evidence_gaps.json").write_text(
        json.dumps(evidence_gaps, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    (out_dir / "stage12_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    (out_dir / "registry_state.json").write_text(
        json.dumps({
            "schema": "stage_12_registry_state_proof_v1",
            "evaluation_run_at": datetime.now(timezone.utc).isoformat(),
            "v1_registry_hashes_before": hashes_before,
        }, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")

    hashes_after = _hash_paths(v1_paths)
    if hashes_before != hashes_after:
        raise RuntimeError(
            f"Stage 12 mutated v1 registry files. "
            f"before={hashes_before}, after={hashes_after}")
    state = json.loads((out_dir / "registry_state.json").read_text(
        encoding="utf-8"))
    state["v1_registry_hashes_after"] = hashes_after
    state["v1_unchanged"] = True
    (out_dir / "registry_state.json").write_text(
        json.dumps(state, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")

    return summary
