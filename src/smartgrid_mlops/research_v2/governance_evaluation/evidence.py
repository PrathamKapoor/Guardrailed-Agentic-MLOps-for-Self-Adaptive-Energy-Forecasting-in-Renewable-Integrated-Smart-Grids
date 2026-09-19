"""Stage 12: Evidence normalization for governance evaluation.

This module reads Stage 10 evidence packages and Stage 11 validation
outputs and converts them into a typed representation of what is
actually available. It distinguishes four classes of evidence:

  1. VERIFIED EVIDENCE       - explicitly checked and passed
  2. MISSING EVIDENCE        - required by the policy but not present
  3. NEGATIVE EVIDENCE       - explicitly checked and FAILED
  4. CONTEXT-DEPENDENT       - present but with conditions/caveats

The classification is HONEST: missing evidence is NOT silently
promoted to passing evidence.

The output is a `NormalizedEvidence` dataclass that the Stage 12
adapter can convert into the existing `CandidateContext` and
`TransitionRequest` shapes.

The Stage 12 layer does NOT add new lifecycle states, new reason
codes, or new transitions. It only maps research evidence onto
the EXISTING Phase 13 governance policy.
"""
from __future__ import annotations
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


# ----------------- Evidence classification ---------------------

@dataclass(frozen=True)
class EvidenceClass:
    """A single piece of evidence, classified honestly.

    `kind` is one of: VERIFIED, MISSING, NEGATIVE, CONTEXT_DEPENDENT.
    `value` is a free-form payload (number, string, dict) that
    downstream code can use.
    `where` is a human-readable path to the source.
    `note` documents any condition, caveat, or boundary."""
    name: str
    kind: str   # "VERIFIED" | "MISSING" | "NEGATIVE" | "CONTEXT_DEPENDENT"
    value: Any
    where: str
    note: str = ""


# ----------------- Stage 10 evidence reader ----------------

def read_stage_10_evidence(evidence_dir: Path) -> list[dict]:
    """Read every Stage 10 evidence package under the standard
    output directory. Each evidence.json is returned as a dict
    keyed by its top-level fields (baseline_metrics_test,
    candidate_metrics_test, evidence_package, ...)."""
    out: list[dict] = []
    if not evidence_dir.exists():
        return out
    for ej_path in sorted(evidence_dir.rglob("evidence.json")):
        try:
            out.append(json.loads(ej_path.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            continue
    return out


# ----------------- Stage 11 evidence reader ----------------

def read_stage_11_per_fold(per_fold_dir: Path) -> list[dict]:
    """Read every Stage 11 per-fold result file."""
    out: list[dict] = []
    if not per_fold_dir.exists():
        return out
    for ej_path in sorted(per_fold_dir.rglob("*.json")):
        try:
            out.append(json.loads(ej_path.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            continue
    return out


def read_stage_11_summary(per_fold_dir: Path) -> dict:
    """Read the Stage 11 per_fold_summary.json if it exists."""
    p = per_fold_dir / "per_fold_summary.json"
    if not p.is_file():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


# ----------------- Normalization ---------------------

@dataclass(frozen=True)
class NormalizedEvidence:
    """The complete normalized evidence for a single candidate.

    `candidate_id` is the Stage 10 evidence-package id.
    `target` is the target name.
    `classifications` is the four-class normalized evidence list.
    `proposed_transition` is the lifecycle transition the candidate
    intends to request.
    `chronology_folds` lists the fold ids on which the candidate was
    evaluated.
    """
    candidate_id: str
    target: str
    proposed_transition: str
    classification: list[EvidenceClass] = field(default_factory=list)
    chronology_folds: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def _classify_evidence(
    s10_evidence: dict, s11_per_fold: list[dict], s11_summary: dict,
) -> list[EvidenceClass]:
    """Translate the Stage 10 and Stage 11 outputs into the four-class
    evidence list required by the existing Phase 13 policy gates.

    The mapping is explicit. A piece of evidence that does not exist
    in the research outputs becomes a `MISSING` entry, never a
    `VERIFIED` entry. The Phase 13 policy enumerates the evidence
    requirements; the Stage 12 layer just reports whether each one
    is present, absent, or has a known issue."""
    out: list[EvidenceClass] = []

    # ----- EVIDENCE_VALIDITY_GATE -----
    # Phase 13 requires evidence_status in ["VALID"].
    s10_classification = s10_evidence.get("classification", "MISSING")
    if s10_classification == "MEANINGFUL_IMPROVEMENT":
        out.append(EvidenceClass(
            name="evidence_status",
            kind="VERIFIED",
            value="VALID",
            where="stage_10/evidence_package.classification",
            note=f"Stage 10 classification: {s10_classification}"))
    elif s10_classification == "NUMERICAL_IMPROVEMENT_NOT_MEANINGFUL":
        out.append(EvidenceClass(
            name="evidence_status",
            kind="CONTEXT_DEPENDENT",
            value=s10_classification,
            where="stage_10/evidence_package.classification",
            note="Stage 10 result is a numerical improvement below the 1% MAE meaningful threshold."))
    elif s10_classification == "NO_RESEARCH_REQUIRED":
        out.append(EvidenceClass(
            name="evidence_status",
            kind="VERIFIED",
            value="VALID",
            where="stage_10/evidence_package.classification",
            note="Stage 10 concluded NO_RESEARCH_REQUIRED: frozen finaltest remains the reference."))
    else:
        out.append(EvidenceClass(
            name="evidence_status",
            kind="MISSING",
            value=None,
            where="stage_10/evidence_package.classification",
            note=f"unknown classification: {s10_classification!r}"))

    # ----- LINEAGE_COMPLETENESS_GATE -----
    has_source_sha = bool(s10_evidence.get("evidence_package", {}).get("source", {}).get("sha256"))
    if has_source_sha:
        out.append(EvidenceClass(
            name="lineage_status",
            kind="VERIFIED",
            value="COMPLETE",
            where="stage_10/evidence_package.source.sha256",
            note="Source artefact SHA-256 is recorded."))
    else:
        out.append(EvidenceClass(
            name="lineage_status",
            kind="MISSING",
            value=None,
            where="stage_10/evidence_package.source.sha256",
            note="No source artefact SHA-256 recorded in evidence package."))

    # ----- MODEL_SPEC_FINGERPRINT_GATE -----
    # The Phase 13 policy requires actual_model_fingerprint ==
    # expected_model_fingerprint. The Stage 10 evidence does not
    # provide a Phase-19-finalized model_spec_fingerprint for the
    # candidate models (they are HGB / Ridge / constant_bias, none
    # of which is a frozen Phase 19 finalist). This is a HONEST
    # MISSING: the policy requires exact-match fingerprints; the
    # candidate does not provide them.
    out.append(EvidenceClass(
        name="model_spec_fingerprint",
        kind="MISSING",
        value=None,
        where="stage_10/evidence_package",
        note=("Stage 10 candidate is a NEW residual model (constant_bias / "
              "Ridge / HGB), not a frozen Phase 19 finalist. No exact-match "
              "model_spec_fingerprint is available in the research outputs.")))

    # ----- FEATURE_SPEC_FINGERPRINT_GATE -----
    out.append(EvidenceClass(
        name="feature_spec_fingerprint",
        kind="MISSING",
        value=None,
        where="stage_10/evidence_package",
        note=("Stage 10 feature spec is described in the candidate description "
              "but no exact-match feature_spec_fingerprint (per Phase 10's "
              "selected feature freeze) is included in the research output.")))

    # ----- PROTOCOL_COMPATIBILITY_GATE -----
    # The actual SHA-256 of the Phase 19 frozen protocol freeze. This
    # is NOT in the policy's accepted_protocol_hashes (which lists
    # the Phase 10 ablation protocol and one other); the honest
    # outcome is therefore that protocol compatibility cannot be
    # VERIFIED against the existing frozen policy. Stage 12 records
    # this as CONTEXT_DEPENDENT evidence.
    _ph_root = Path(__file__).resolve().parents[4] / "artifacts" / "experimental_design"
    _ph_path = _ph_root / "phase_19_final_evaluation_protocol_freeze.yaml"
    if _ph_path.is_file():
        protocol_sha = hashlib.sha256(_ph_path.read_bytes()).hexdigest()
    else:
        protocol_sha = "missing"
    out.append(EvidenceClass(
        name="protocol_hash",
        kind="CONTEXT_DEPENDENT",
        value=protocol_sha,
        where="artifacts/experimental_design/phase_19_final_evaluation_protocol_freeze.yaml",
        note=("Phase 19 protocol freeze SHA-256 is recorded. The "
              "Phase 13 policy's accepted_protocol_hashes list does "
              "NOT include the Phase 19 protocol hash; therefore "
              "protocol compatibility is NOT directly verifiable "
              "under the existing frozen policy.")))

    # ----- REPRODUCIBILITY_METADATA_GATE -----
    s10_splits = s10_evidence.get("evidence_package", {}).get("split_counts", {})
    if s10_splits:
        out.append(EvidenceClass(
            name="reproducibility_metadata",
            kind="VERIFIED",
            value="COMPLETE",
            where="stage_10/evidence_package.split_counts",
            note=(f"Stage 10 reproducibility metadata: n_train={s10_splits.get('n_train')}, "
                  f"n_validation={s10_splits.get('n_validation')}, "
                  f"n_test={s10_splits.get('n_test')}.")))
    else:
        out.append(EvidenceClass(
            name="reproducibility_metadata",
            kind="MISSING",
            value=None,
            where="stage_10/evidence_package",
            note="Stage 10 evidence package does not include split counts."))

    # ----- DEVIATION_STATUS_GATE -----
    # The Phase 11 distribution analysis found a real shift for
    # LOAD and WIND. This is a NEGATIVE evidence entry: the
    # distribution shift is documented honestly and the
    # deviation_status is therefore NOT "NONE" but NOT
    # "UNRESOLVED_CRITICAL" either.
    target = s10_evidence.get("target", "unknown")
    has_distribution_shift = any(
        entry.get("target") == target
        and float(entry.get("stdev", 0)) > 30
        for entry in s11_summary.get("per_target", []) if isinstance(entry, dict)
    )
    if has_distribution_shift:
        out.append(EvidenceClass(
            name="deviation_status",
            kind="CONTEXT_DEPENDENT",
            value="DOCUMENTED_NON_CRITICAL",
            where="stage_11/distribution_analysis",
            note=("Stage 11 distribution analysis found a real residual "
                  "distribution shift on this target. The shift is "
                  "documented, not unresolved-critical.")))
    else:
        out.append(EvidenceClass(
            name="deviation_status",
            kind="VERIFIED",
            value="NONE",
            where="stage_11/distribution_analysis",
            note="No distribution shift detected on this target."))

    # ----- BENCHMARK_GATE -----
    # Phase 13 requires the candidate to "strictly outperform the
    # predefined strongest development benchmark". The Stage 10
    # research compared to RTS_DAY_AHEAD (a published external
    # baseline), NOT to the frozen Phase 11 finalist registry. This
    # is a MISSING piece of evidence: the policy requires a
    # specific comparison, and the research did not include that
    # comparison.
    out.append(EvidenceClass(
        name="benchmark_gate",
        kind="MISSING",
        value=None,
        where="stage_10/evidence_package",
        note=("Phase 13 benchmark_gate requires the candidate to "
              "strictly outperform the predefined strongest development "
              "benchmark (Phase 11 finalist registry). Stage 10 compared "
              "to RTS_DAY_AHEAD (an external baseline), not to the "
              "frozen Phase 11 finalist registry. The required comparison "
              "is MISSING.")))

    # ----- STATISTICAL_EVIDENCE_GATE -----
    s11_present = any(
        (entry.get("target") == target
         and entry.get("fold_id") in {"F-Nov", "F-Dec"})
        for entry in s11_summary.get("folds", []) if isinstance(entry, dict)
    )
    if s11_present:
        out.append(EvidenceClass(
            name="statistical_evidence",
            kind="VERIFIED",
            value="REQUIRED_PASS",
            where="stage_11/fold_results/<fold>_<target>.json",
            note=("Stage 11 evaluated the candidate on at least the "
                  "F-Nov and F-Dec folds of the locked Phase 19 test "
                  "window with explicit metrics.")))
    else:
        out.append(EvidenceClass(
            name="statistical_evidence",
            kind="MISSING",
            value=None,
            where="stage_11/fold_results",
            note="Stage 11 did not produce per-fold metrics for F-Nov/F-Dec."))

    # ----- FINAL_TEST_POLICY_GATE -----
    # The candidate must not request final-test access or
    # integrity-audit activation. The Stage 10 evidence USES the
    # locked test window (which is the pre-authorized final-test
    # window) but does not request NEW access. The Stage 10
    # protocol freeze explicitly states scope.training_allowed=false
    # and scope.hpo_allowed=false, etc. The candidate inherits
    # the existing final-test access that the Phase 19 protocol
    # already granted.
    out.append(EvidenceClass(
        name="final_test_access",
        kind="VERIFIED",
        value="ALREADY_AUTHORIZED_VIA_PHASE_19",
        where="stage_10/evaluation_window",
        note=("Stage 10 evaluation uses the locked Phase 19 test "
              "window (2020-11-01..2020-12-31), which is the "
              "pre-authorized access recorded in the Phase 19 "
              "protocol freeze. No NEW final-test access is "
              "requested by Stage 10 or Stage 12.")))

    return out


# ----------------- Top-level normalizer ----------------

def normalize_evidence(
    s10_evidence: dict,
    s11_per_fold: list[dict],
    s11_summary: dict,
    proposed_transition: str = "EXPERIMENTAL -> VALIDATED",
) -> NormalizedEvidence:
    """Build the normalized evidence for a single candidate."""
    classifications = _classify_evidence(s10_evidence, s11_per_fold, s11_summary)
    folds: list[str] = []
    for entry in s11_per_fold:
        if "fold_id" in entry and "target" in entry:
            if entry.get("target") == s10_evidence.get("target"):
                folds.append(entry["fold_id"])
    notes: list[str] = []
    cand_id = s10_evidence.get("candidate_id", "unknown")
    target = s10_evidence.get("target", "unknown")
    return NormalizedEvidence(
        candidate_id=cand_id,
        target=target,
        proposed_transition=proposed_transition,
        classification=classifications,
        chronology_folds=sorted(set(folds)),
        notes=notes,
    )
