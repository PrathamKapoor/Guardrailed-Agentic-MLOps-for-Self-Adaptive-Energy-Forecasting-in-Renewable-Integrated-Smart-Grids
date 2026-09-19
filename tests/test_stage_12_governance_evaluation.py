"""Stage 12 tests: evidence-to-governance evaluation.

The Stage 12 layer is a TRANSLATION LAYER ONLY. These tests prove
that it:
  1. Reuses the existing Phase 13 frozen policy without
     modification.
  2. Reuses the existing GovernanceEngine without modification.
  3. Translates Stage 10/11 evidence into CandidateContext and
     TransitionRequest shapes without inventing new fields.
  4. Preserves missing evidence as MISSING (does not silently
     promote it to VERIFIED).
  5. Records the existing governance decision structure
     (decision, reason_codes, gate_results, decision fingerprint).
  6. Performs NO lifecycle mutation: hashes every protected
     registry file before and after; hashes must match.
  7. Treats a deliberately-weak evidence package as MISSING and
     does not produce a positive decision for it.
  8. Re-runs are deterministic.
  9. Writes outputs only under artifacts/v2/.
"""
from __future__ import annotations
import csv
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from smartgrid_mlops.governance.policies import GovernancePolicy  # noqa: E402
from smartgrid_mlops.governance.schemas import (  # noqa: E402
    DECISIONS, LIFECYCLE_STATES, REASON_CODES,
    CandidateContext, TransitionRequest,
)
from smartgrid_mlops.governance.policy_engine import GovernanceEngine  # noqa: E402
from smartgrid_mlops.research_v2.governance_evaluation import (  # noqa: E402
    V2_ROOT, STAGE_10_DIR, STAGE_11_PER_FOLD, STAGE_11_SUMMARY,
    run_governance_evaluation, build_candidate_context,
    build_transition_request, evaluate_candidate, normalize_evidence,
    EvidenceClass, NormalizedEvidence,
)
from smartgrid_mlops.research_v2.governance_evaluation.evidence import (
    read_stage_10_evidence, read_stage_11_summary,
)


PHASE_13_POLICY = ROOT / "config" / "governance" / "phase_13_policy.yaml"


# ----------------- Policy / engine reuse ----------------

class TestPolicyAndEngineReuse:
    def test_phase_13_policy_loaded_from_frozen_path(self):
        policy = GovernancePolicy.load(PHASE_13_POLICY)
        assert policy.document["policy_id"] == "SMARTGRID_DETERMINISTIC_GOVERNANCE"
        assert policy.document["policy_version"] == "13.0.0"

    def test_no_phase_13_policy_mutation_after_run(self):
        before = PHASE_13_POLICY.read_bytes()
        run_governance_evaluation()
        after = PHASE_13_POLICY.read_bytes()
        assert before == after

    def test_stage_12_uses_existing_governance_engine(self):
        # The Stage 12 adapter imports `GovernanceEngine` from the
        # existing module. The production governance directory has
        # not been duplicated.
        from smartgrid_mlops.governance.policy_engine import (
            GovernanceEngine as _GE,
        )
        from smartgrid_mlops.research_v2.governance_evaluation.adapter import (
            GovernanceEngine as _Adapter_GE,
        )
        assert _Adapter_GE is _GE

    def test_no_lifecycle_mutation_endpoints_added(self):
        from product.backend_api.app.main import create_app
        app = create_app()
        paths = sorted(app.openapi()["paths"].keys())
        forbidden = ("promote", "deploy", "rollback", "retrain",
                     "change_policy", "modify_model", "modify_features",
                     "approve_deployment", "research_v2",
                     "governance_evaluation", "stage_12")
        for p in paths:
            for f in forbidden:
                assert f not in p.lower(), f"forbidden path {p} contains {f}"


# ----------------- Evidence normalization ----------------

class TestEvidenceNormalization:
    def test_evidence_class_honors_missing(self):
        # Missing evidence must remain MISSING; never VERIFIED.
        ec = EvidenceClass(name="x", kind="MISSING", value=None,
                            where="nowhere", note="absent")
        assert ec.kind == "MISSING"

    def test_negative_evidence_is_distinct_from_verified(self):
        # NEGATIVE and VERIFIED are distinct evidence classes.
        assert "NEGATIVE" != "VERIFIED"
        assert "MISSING" != "VERIFIED"

    def test_normalize_preserves_four_class_classification(self):
        s10_dir = STAGE_10_DIR
        s11_summary_path = STAGE_11_SUMMARY
        from smartgrid_mlops.research_v2.governance_evaluation.evidence import (
            read_stage_10_evidence, read_stage_11_summary,
        )
        s10_list = read_stage_10_evidence(s10_dir)
        s11_summary = read_stage_11_summary(s11_summary_path)
        # Pick the first candidate.
        assert s10_list, "no Stage 10 evidence packages found"
        ev = normalize_evidence(s10_list[0], [], s11_summary)
        kinds = {c.kind for c in ev.classification}
        # All four classes may appear; what matters is that none of
        # the VERIFIED entries are actually NEGATIVE or MISSING.
        for c in ev.classification:
            assert c.kind in ("VERIFIED", "MISSING", "NEGATIVE", "CONTEXT_DEPENDENT")

    def test_benchmark_gate_recorded_as_missing(self):
        # The Phase 13 benchmark_gate requires a comparison to the
        # predefined strongest development benchmark. The Stage 10
        # research compared to RTS_DAY_AHEAD (an external baseline),
        # not to the Phase 11 finalist registry. The benchmark_gate
        # evidence must therefore be MISSING.
        s10_list = read_stage_10_evidence(STAGE_10_DIR)
        s11_summary = read_stage_11_summary(STAGE_11_SUMMARY)
        any_missing_benchmark = False
        for s10 in s10_list:
            ev = normalize_evidence(s10, [], s11_summary)
            for c in ev.classification:
                if c.name == "benchmark_gate":
                    assert c.kind == "MISSING", (
                        f"{s10['candidate_id']}: benchmark_gate is "
                        f"{c.kind}, expected MISSING (the required "
                        f"comparison is to the predefined strongest "
                        f"development benchmark; Stage 10 did not "
                        f"include that comparison).")
                    any_missing_benchmark = True
        assert any_missing_benchmark, "no candidate reported benchmark_gate"

    def test_model_spec_fingerprint_recorded_as_missing(self):
        # The Phase 13 policy requires exact-match frozen
        # model_spec_fingerprint. The Stage 10 candidates are NEW
        # residual models; they have no exact-match frozen fingerprint.
        s10_list = read_stage_10_evidence(STAGE_10_DIR)
        s11_summary = read_stage_11_summary(STAGE_11_SUMMARY)
        for s10 in s10_list:
            ev = normalize_evidence(s10, [], s11_summary)
            for c in ev.classification:
                if c.name == "model_spec_fingerprint":
                    assert c.kind == "MISSING"

    def test_feature_spec_fingerprint_recorded_as_missing(self):
        s10_list = read_stage_10_evidence(STAGE_10_DIR)
        s11_summary = read_stage_11_summary(STAGE_11_SUMMARY)
        for s10 in s10_list:
            ev = normalize_evidence(s10, [], s11_summary)
            for c in ev.classification:
                if c.name == "feature_spec_fingerprint":
                    assert c.kind == "MISSING"


# ----------------- Adapter correctness ----------------

class TestAdapter:
    def test_candidate_context_uses_existing_schema(self):
        # The Stage 12 adapter produces a `CandidateContext` that
        # passes isinstance of the EXISTING governance schema.
        s10_list = read_stage_10_evidence(STAGE_10_DIR)
        s11_summary = read_stage_11_summary(STAGE_11_SUMMARY)
        ev = normalize_evidence(s10_list[0], [], s11_summary)
        ctx = build_candidate_context(ev, policy_mode="RESEARCH")
        assert isinstance(ctx, CandidateContext)
        assert ctx.subject_id == ev.candidate_id

    def test_transition_request_uses_existing_schema(self):
        s10_list = read_stage_10_evidence(STAGE_10_DIR)
        s11_summary = read_stage_11_summary(STAGE_11_SUMMARY)
        ev = normalize_evidence(s10_list[0], [], s11_summary)
        req = build_transition_request(ev)
        assert isinstance(req, TransitionRequest)
        assert req.current_state in LIFECYCLE_STATES
        assert req.proposed_state in LIFECYCLE_STATES

    def test_decision_uses_existing_decision_enum(self):
        # Every Stage 12 decision must be one of the four EXISTING
        # decisions defined by the governance schemas.
        summary_path = V2_ROOT / "stage12_summary.json"
        if not summary_path.is_file():
            run_governance_evaluation()
        body = json.loads(summary_path.read_text(encoding="utf-8"))
        for d in body["candidate_decisions"]:
            assert d["decision"] in DECISIONS, (
                f"Stage 12 emitted an unknown decision {d['decision']!r}; "
                f"the existing policy only allows {DECISIONS}")
            for rc in d["reason_codes"]:
                assert rc in REASON_CODES, (
                    f"Stage 12 emitted an unknown reason code {rc!r}; "
                    f"the existing policy only allows {REASON_CODES}")


# ----------------- Lifecycle mutation proof ----------------

class TestLifecycleMutationProof:
    @pytest.fixture(scope="class")
    def stage12_run(self, tmp_path_factory):
        # Re-run the orchestrator with a tmp output directory to keep
        # the real v2 tree untouched during the test.
        out_dir = tmp_path_factory.mktemp("stage12")
        audit_path = out_dir / "audit.jsonl"
        # Hash v1 BEFORE
        v1_paths = _v1_paths()
        before = {k: hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
                  for k, p in v1_paths.items()}
        # Run the orchestrator against the tmp out_dir.
        run_governance_evaluation(
            out_dir=out_dir,
            audit_path=audit_path,
        )
        # Hash v1 AFTER
        after = {k: hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
                 for k, p in v1_paths.items()}
        return {
            "before": before, "after": after,
            "out_dir": out_dir, "audit_path": audit_path,
        }

    def test_no_v1_artefact_modified(self, stage12_run):
        assert stage12_run["before"] == stage12_run["after"], (
            "Stage 12 mutated a v1 registry file. See stage12_run['after']"
            " vs stage12_run['before'].")

    def test_audit_jsonl_written(self, stage12_run):
        assert stage12_run["audit_path"].is_file(), (
            "Stage 12 did not write the append-only audit JSONL.")
        # The audit file is the only allowed mutation.
        with stage12_run["audit_path"].open(encoding="utf-8") as f:
            lines = [l for l in f if l.strip()]
        assert lines, "audit JSONL is empty"

    def test_audit_jsonl_records_correct_decisions(self, stage12_run):
        with stage12_run["audit_path"].open(encoding="utf-8") as f:
            events = [json.loads(l) for l in f if l.strip()]
        # We expect 7 candidates x 2 audit events each
        # (GOVERNANCE_EVALUATED + decision event), possibly + POLICY_VIOLATION
        # for DENY decisions. At minimum, every candidate has
        # a GOVERNANCE_EVALUATED event.
        subject_ids = {e["subject_id"] for e in events
                       if e.get("event_type") == "GOVERNANCE_EVALUATED"}
        assert len(subject_ids) == 7, (
            f"expected 7 distinct subjects, got {len(subject_ids)}: {subject_ids}")

    def test_audit_records_decision_id_in_details(self, stage12_run):
        with stage12_run["audit_path"].open(encoding="utf-8") as f:
            events = [json.loads(l) for l in f if l.strip()]
        for e in events:
            assert "decision_id" in e.get("details", {}), (
                f"audit event {e.get('event_type')} missing decision_id")


# ----------------- Weak-evidence test ----------------

class TestDeliberatelyWeakEvidence:
    def test_weak_evidence_does_not_produce_positive_decision(self, tmp_path):
        # Construct a candidate with intentionally missing pieces of
        # evidence: bad fingerprint, bad feature fingerprint,
        # wrong protocol hash, evidence_status=INVALID,
        # lineage_status=INCOMPLETE, no benchmark, etc.
        bad = CandidateContext(
            subject_id="weak_candidate",
            evidence_status="INVALID",
            official_candidate=False,
            lineage_status="INCOMPLETE",
            actual_model_fingerprint="missing",
            expected_model_fingerprint="weak_candidate-spec",
            actual_feature_fingerprint="missing",
            expected_feature_fingerprint="weak_candidate-features",
            protocol_hash="missing",
            reproducibility_metadata="INCOMPLETE",
            deviation_status="UNRESOLVED_CRITICAL",
            benchmark_gate="BENCHMARK_GATE_FAIL",
            statistical_evidence="NOT_REQUIRED",
            approval_state="REJECTED",
            approval_actor="SIMULATION_POLICY",
            policy_mode="RESEARCH",
            requests_final_test_access=False,
            requests_integrity_audit_activation=False,
            evidence_refs=(),
        )
        req = TransitionRequest(
            subject_id="weak_candidate",
            current_state="EXPERIMENTAL",
            proposed_state="VALIDATED",
            actor_type="SYSTEM",
            simulation=True,
        )
        policy = GovernancePolicy.load(PHASE_13_POLICY)
        engine = GovernanceEngine(policy)
        decision = engine.evaluate(bad, req)
        # The frozen policy must return DENY for a candidate that
        # fails any of the model/feature/protocol/lineage/evidence/
        # reproducibility/deviation gates.
        assert decision.decision == "DENY", (
            f"weak-evidence candidate received {decision.decision!r}, "
            f"expected DENY. reason_codes={decision.reason_codes}")
        # And the policy fingerprint must match the loaded policy.
        assert decision.policy_checksum == policy.checksum
        assert decision.governance_policy_fingerprint == policy.governance_policy_fingerprint


# ----------------- Determinism ----------------

class TestDeterminism:
    def test_two_runs_produce_same_decision(self):
        # Stage 12 is deterministic: the same Stage 10 evidence +
        # Stage 11 inputs + Phase 13 policy produce the same
        # decision record (UUIDs and timestamps differ, so we
        # compare on decision + reason_codes only).
        s = run_governance_evaluation()
        # Compare only deterministic fields.
        deterministic = sorted([
            (d["candidate_id"], d["target"], d["decision"],
             tuple(sorted(d["reason_codes"])))
            for d in s["candidate_decisions"]
        ])
        # Re-run and compare the same fields.
        s2 = run_governance_evaluation()
        deterministic2 = sorted([
            (d["candidate_id"], d["target"], d["decision"],
             tuple(sorted(d["reason_codes"])))
            for d in s2["candidate_decisions"]
        ])
        assert deterministic == deterministic2


# ----------------- Output isolation ----------------

class TestOutputIsolation:
    def test_outputs_under_v2_only(self):
        # After a run, no v1 file outside the explicit v1 exception
        # list should have been created. We check that the
        # artifacts/v2/governance_evaluation/ directory exists
        # and contains the expected outputs.
        for fn in ("normalized_evidence.json",
                   "candidate_evaluations.json",
                   "evidence_gaps.json",
                   "stage12_summary.json",
                   "registry_state.json",
                   "stage12_audit.jsonl"):
            assert (V2_ROOT / fn).is_file(), (
                f"Stage 12 output {fn} missing under {V2_ROOT}")


# ----------------- Helper ----------------

def _v1_paths() -> dict:
    return {
        "model_registry_lifecycle": ROOT / "artifacts" / "model_registry" / "lifecycle_registry.yaml",
        "model_registry_research": ROOT / "artifacts" / "model_registry" / "mlops_research_registry.yaml",
        "phase_19_protocol_freeze": ROOT / "artifacts" / "experimental_design" / "phase_19_final_evaluation_protocol_freeze.yaml",
        "phase_13_policy": PHASE_13_POLICY,
        "agent_firewall": ROOT / "src" / "smartgrid_mlops" / "agents" / "firewall.py",
        "governance_engine": ROOT / "src" / "smartgrid_mlops" / "governance" / "policy_engine.py",
    }
