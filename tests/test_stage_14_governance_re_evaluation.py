"""Stage 14 tests: governance-compatible candidate re-evaluation.

Tests verify that Stage 14:
  1. Loads every Stage 13 candidate package and validates
     checksums (Package integrity).
  2. Maps the package into the EXISTING CandidateContext and
     TransitionRequest without silently substituting evidence.
  3. Calls the EXISTING frozen GovernanceEngine (not a parallel
     engine).
  4. Records the actual decisions and reason codes (Adapter +
     Evaluation).
  5. Performs NO lifecycle mutation: hashes of all v1 paths and
     the Phase 13 policy are unchanged.
  6. Re-runs are deterministic.
  7. The agent firewall still blocks all 7 lifecycle actions.
"""
from __future__ import annotations
import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from smartgrid_mlops.governance_re_evaluation import (  # noqa: E402
    V2_ROOT, STAGE_13_ROOT, STAGE_14_ROOT, STAGE_14_AUDIT_PATH,
    GATE_RESULTS_DIR,
    load_all_packages, load_package, PackageIntegrityError,
    list_candidate_ids, adapt, evaluate_candidate, run_reevaluation,
)
from smartgrid_mlops.research_v2.governance_candidate_packages import (  # noqa: E402
    PHASE_19_PROTOCOL_FREEZE as S13_PHASE_19,
)
from smartgrid_mlops.governance.schemas import (  # noqa: E402
    CandidateContext, TransitionRequest, LIFECYCLE_STATES,
    DECISIONS, REASON_CODES,
)
from smartgrid_mlops.governance.policies import GovernancePolicy  # noqa: E402
from smartgrid_mlops.governance.policy_engine import GovernanceEngine  # noqa: E402


CANDIDATE_IDS: tuple[str, ...] = (
    "residual_constant_bias_system_load",
    "residual_constant_bias_wind",
    "residual_ridge_system_load",
    "residual_ridge_wind",
    "residual_hgb_system_load",
    "residual_hgb_wind",
    "residual_no_research_pv",
)


# ---------------- Package integrity ----------------

class TestPackageIntegrity:
    def test_all_seven_candidate_packages_load(self):
        pkgs = load_all_packages()
        assert len(pkgs) == 7, f"expected 7 packages, got {len(pkgs)}"
        for p in pkgs:
            assert p.integrity_ok
            # Required files are present in the package.
            for fn in ("candidate_manifest.json", "model_spec.json",
                        "feature_spec.json", "data_split_manifest.json",
                        "benchmark_evaluation.json",
                        "protocol_compatibility.json",
                        "reproducibility_manifest.json",
                        "checksums.json"):
                assert fn in p.files

    def test_each_candidate_has_all_required_files(self):
        for cid in CANDIDATE_IDS:
            p = load_package(cid)
            for fn in ("candidate_manifest.json", "model_spec.json",
                        "feature_spec.json", "data_split_manifest.json",
                        "benchmark_evaluation.json",
                        "protocol_compatibility.json",
                        "reproducibility_manifest.json",
                        "checksums.json"):
                assert fn in p.files, f"{cid}: missing {fn}"

    def test_recording_checksums_match_actual_hashes(self):
        for cid in CANDIDATE_IDS:
            p = load_package(cid)
            cs = p.file("checksums.json")
            for fn, expected in cs["file_hashes_sha256"].items():
                actual = hashlib.sha256(
                    (p.package_dir / fn).read_bytes()).hexdigest()
                assert actual == expected, (
                    f"{cid}/{fn}: recorded={expected} actual={actual}")

    def test_missing_file_fails_honestly(self, tmp_path):
        # Create a stub package and break it: remove a required file.
        # The loader must raise PackageIntegrityError, NOT silently
        # return VERIFIED.
        from smartgrid_mlops.governance_re_evaluation.loader import (
            REQUIRED_FILES,
        )
        stub = tmp_path / "broken_pkg"
        stub.mkdir()
        for fn in REQUIRED_FILES:
            (stub / fn).write_text("{}")
        # Remove one file.
        (stub / "model_spec.json").unlink()
        with pytest.raises(PackageIntegrityError):
            load_package("broken_pkg", packages_root=tmp_path)

    def test_invalid_checksum_fails_honestly(self, tmp_path):
        from smartgrid_mlops.governance_re_evaluation.loader import (
            REQUIRED_FILES,
        )
        stub = tmp_path / "tampered_pkg"
        stub.mkdir()
        for fn in REQUIRED_FILES:
            (stub / fn).write_text("{}")
        # Corrupt the checksums.json: claim a wrong aggregate.
        (stub / "checksums.json").write_text(json.dumps({
            "file_hashes_sha256": {
                fn: hashlib.sha256((stub / fn).read_bytes()).hexdigest()
                for fn in REQUIRED_FILES if fn != "checksums.json"
            },
            "aggregate_package_sha256": "0" * 64,  # wrong
        }))
        with pytest.raises(PackageIntegrityError):
            load_package("tampered_pkg", packages_root=tmp_path)


# ---------------- Adapter ----------------

class TestAdapter:
    def test_candidate_context_uses_existing_schema(self):
        for cid in CANDIDATE_IDS:
            p = load_package(cid)
            adapted = adapt(p)
            assert isinstance(adapted.candidate_context, CandidateContext)
            assert adapted.candidate_context.subject_id == cid

    def test_transition_request_uses_existing_schema(self):
        for cid in CANDIDATE_IDS:
            p = load_package(cid)
            adapted = adapt(p)
            assert isinstance(adapted.transition_request, TransitionRequest)
            assert adapted.transition_request.current_state in LIFECYCLE_STATES
            assert adapted.transition_request.proposed_state in LIFECYCLE_STATES

    def test_fingerprints_are_taken_from_package_not_fabricated(self):
        # The fingerprint must equal the value recorded in the
        # package; the adapter must NOT compute a different value.
        for cid in CANDIDATE_IDS:
            p = load_package(cid)
            adapted = adapt(p)
            expected_model = p.file("model_spec.json")["model_spec_fingerprint"]
            expected_feature = p.file("feature_spec.json")["feature_spec_fingerprint"]
            assert adapted.model_spec_fingerprint == expected_model
            assert adapted.feature_spec_fingerprint == expected_feature

    def test_no_research_pv_records_n_a_fingerprints(self):
        p = load_package("residual_no_research_pv")
        adapted = adapt(p)
        # The no_research pathway uses the frozen Phase 11
        # random_forest reference; its model_spec and feature_spec
        # are recorded as n/a in the Stage 13 package.
        ms = p.file("model_spec.json")["model_spec_fingerprint"]
        fs = p.file("feature_spec.json")["feature_spec_fingerprint"]
        # The adapter reports the package's values verbatim.
        assert adapted.model_spec_fingerprint == ms
        assert adapted.feature_spec_fingerprint == fs

    def test_evidence_gaps_recorded_honestly(self):
        p = load_package("residual_constant_bias_wind")
        adapted = adapt(p)
        # The constant_bias_wind package records
        # BENCHMARK_GATE_FAIL and REQUIRES_NEW_PROTOCOL_APPROVAL;
        # the adapter must record these as gaps.
        names = {g.gate for g in adapted.evidence_gaps}
        assert "PROTOCOL_COMPATIBILITY_GATE" in names
        # The constant_bias_wind candidate's benchmark is
        # BENCHMARK_GATE_FAIL (from the Stage 13 evaluation),
        # which the adapter surfaces as a benchmark-related gap.
        benchmark_gaps = [g for g in adapted.evidence_gaps
                          if "BENCHMARK" in g.gate.upper()]
        assert benchmark_gaps, (
            f"expected a benchmark-related gap; got {names}")


# ---------------- Evaluation ----------------

class TestEvaluation:
    def test_all_seven_candidates_evaluated(self):
        s = run_reevaluation()
        assert s["n_candidates_evaluated"] == 7
        assert s["n_load_failures"] == 0

    def test_decisions_contain_actual_governance_decision_fields(self):
        s = run_reevaluation()
        for d in s["decisions"]:
            assert d["decision"] in DECISIONS, (
                f"decision {d['decision']!r} not in {DECISIONS}")
            for rc in d["reason_codes"]:
                assert rc in REASON_CODES, (
                    f"reason_code {rc!r} not in {REASON_CODES}")
            assert "ordered_gate_results" in d
            assert "policy_id" in d
            assert "policy_version" in d
            assert "policy_checksum" in d
            assert "governance_policy_fingerprint" in d
            assert "decision_content_fingerprint" in d

    def test_existing_governance_engine_is_invoked(self):
        # The Stage 14 evaluator imports the EXISTING
        # GovernanceEngine; it does not fork.
        from smartgrid_mlops.governance_re_evaluation import evaluator
        from smartgrid_mlops.governance import policy_engine as _pe
        assert evaluator.GovernanceEngine is _pe.GovernanceEngine

    def test_existing_frozen_policy_is_used(self):
        # The Phase 13 policy checksum must match the recorded value.
        s = run_reevaluation()
        expected = "ee13cb365f43aefa154bff3092f22de938eb3d61cd94ec0f5c6fc521ef72c862"
        assert s["policy_checksum"] == expected
        # And the package on disk is unchanged.
        policy_path = ROOT / "config" / "governance" / "phase_13_policy.yaml"
        actual = hashlib.sha256(policy_path.read_bytes()).hexdigest()
        assert actual == expected


# ---------------- Safety boundaries ----------------

class TestSafetyBoundaries:
    def _hash_v1_paths(self) -> dict[str, str]:
        paths = {
            "phase_13_policy": ROOT / "config" / "governance" / "phase_13_policy.yaml",
            "phase_19_protocol_freeze": (
                ROOT / "artifacts" / "experimental_design"
                / "phase_19_final_evaluation_protocol_freeze.yaml"
            ),
            "model_registry_lifecycle": (
                ROOT / "artifacts" / "model_registry" / "lifecycle_registry.yaml"
            ),
            "model_registry_research": (
                ROOT / "artifacts" / "model_registry" / "mlops_research_registry.yaml"
            ),
            "agent_firewall": ROOT / "src" / "smartgrid_mlops" / "agents" / "firewall.py",
            "governance_engine": (
                ROOT / "src" / "smartgrid_mlops" / "governance" / "policy_engine.py"
            ),
        }
        return {k: hashlib.sha256(p.read_bytes()).hexdigest()
                for k, p in paths.items() if p.is_file()}

    def test_no_v1_artefact_modified_by_reevaluation(self):
        before = self._hash_v1_paths()
        run_reevaluation()
        after = self._hash_v1_paths()
        assert before == after, (
            f"Stage 14 mutated a v1 path. before={before}, after={after}")

    def test_no_phase_19_protected_artefact_modified(self):
        baseline = json.loads(
            (ROOT / "artifacts" / "ui_build" / "phase19_integrity_baseline.json"
             ).read_text(encoding="utf-8"))
        def _hash():
            ok = fail = 0
            for rel, meta in baseline.items():
                if not isinstance(meta, dict) or "sha256" not in meta: continue
                p = ROOT / rel
                if not p.is_file(): continue
                h = hashlib.sha256(p.read_bytes()).hexdigest()
                if h == meta["sha256"] and p.stat().st_size == meta["size"]:
                    ok += 1
                else:
                    fail += 1
            return ok, fail
        before_ok, before_fail = _hash()
        run_reevaluation()
        after_ok, after_fail = _hash()
        assert (before_ok, before_fail) == (after_ok, after_fail), (
            f"Stage 14 mutated a Phase 19 protected artefact: "
            f"before_ok={before_ok}, after_ok={after_ok}, "
            f"before_fail={before_fail}, after_fail={after_fail}")

    def test_no_lifecycle_mutation_endpoints_added(self):
        from product.backend_api.app.main import create_app
        app = create_app()
        paths = sorted(app.openapi()["paths"].keys())
        forbidden = ("promote", "deploy", "rollback", "retrain",
                     "change_policy", "modify_model", "modify_features",
                     "approve_deployment", "stage_14",
                     "governance_re_evaluation")
        for p in paths:
            for f in forbidden:
                assert f not in p.lower(), (
                    f"forbidden path {p} contains {f}")

    def test_agent_firewall_still_blocks_all_seven(self):
        from smartgrid_mlops.agents.firewall import firewall_validate
        from smartgrid_mlops.agents.schemas import ALLOWED_RECOMMENDATIONS
        for blocked in ("PROMOTE_MODEL", "DEPLOY", "ROLLBACK_MODEL",
                        "START_RETRAINING", "CHANGE_POLICY",
                        "CHANGE_FEATURES", "MODIFY_MODEL"):
            assert not firewall_validate(blocked).allowed
        for allowed in ALLOWED_RECOMMENDATIONS:
            assert firewall_validate(allowed).allowed

    def test_no_lifecycle_state_mutation(self):
        # The Stage 14 lifecycle registry must be byte-identical
        # before and after the run.
        reg = ROOT / "artifacts" / "model_registry" / "lifecycle_registry.yaml"
        before = reg.read_bytes()
        run_reevaluation()
        after = reg.read_bytes()
        assert before == after


# ---------------- Determinism ----------------

class TestDeterminism:
    def test_two_runs_produce_same_per_candidate_decisions(self):
        s1 = run_reevaluation()
        s2 = run_reevaluation()
        for d1, d2 in zip(s1["decisions"], s2["decisions"]):
            assert d1["subject_id"] == d2["subject_id"]
            assert d1["decision"] == d2["decision"]
            assert d1["reason_codes"] == d2["reason_codes"]
            assert d1["decision_content_fingerprint"] == d2["decision_content_fingerprint"]

    def test_summary_counts_are_stable(self):
        s1 = run_reevaluation()
        s2 = run_reevaluation()
        assert s1["decision_counts"] == s2["decision_counts"]
        assert s1["reason_code_counts"] == s2["reason_code_counts"]
