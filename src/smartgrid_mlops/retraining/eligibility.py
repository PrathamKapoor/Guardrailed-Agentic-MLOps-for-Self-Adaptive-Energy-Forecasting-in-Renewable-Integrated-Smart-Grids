"""Deterministic retraining eligibility gates. No bare booleans: every evaluation
returns a structured decision with per-gate outcomes and ordered reason codes."""
from __future__ import annotations
from datetime import datetime
from .policy import RetrainingPolicy
from .requests import find_existing_decision
from .schemas import GateOutcome, RetrainingDecision, RetrainingRequest

SEVERITY_RANK = {"NONE": 0, "WATCH": 1, "WARNING": 2, "CRITICAL": 3}


def _outcome(gate, passed, reason, ok, fail):
    return GateOutcome(gate, passed, None if passed else reason, ok if passed else fail)


def _policy_version_gate(r: RetrainingRequest, p: RetrainingPolicy, ctx):
    passed = (r.claimed_policy_id in (None, p.policy_id)
              and r.claimed_policy_version in (None, p.version)
              and r.claimed_policy_checksum in (None, p.checksum))
    return _outcome("POLICY_VERSION_GATE", passed, "POLICY_VERSION_MISMATCH",
                    "Retraining policy identity matches.", "Claimed retraining policy identity does not match the frozen policy.")


def _origin_gate(r: RetrainingRequest, p: RetrainingPolicy, ctx):
    passed = r.request_origin in p.document["request_origins_allowed"] and r.request_origin != "AGENT"
    return _outcome("REQUEST_ORIGIN_GATE", passed, "REQUEST_ORIGIN_INVALID",
                    "Request origin is allowed and deterministic.", "Request origin is not an allowed deterministic origin.")


def _evidence_gate(r: RetrainingRequest, p: RetrainingPolicy, ctx):
    valid_status = r.evidence_status == "VALID"
    has_events = len(r.triggering_drift_event_ids) > 0
    events_valid = ctx is not None and ctx.known_event_ids is not None and all(
        e in ctx.known_event_ids for e in r.triggering_drift_event_ids)
    passed = valid_status and has_events and (ctx is None or ctx.trusts_evidence or events_valid)
    return _outcome("DRIFT_EVIDENCE_GATE", passed, "DRIFT_EVIDENCE_INVALID",
                    "Referenced Phase 14-style monitoring evidence exists and is VALID.",
                    "Referenced drift evidence is missing, non-evidence smoke, or unknown.")


def _severity_gate(r: RetrainingRequest, p: RetrainingPolicy, ctx):
    rule = p.document["severity_policy"].get(r.trigger_severity, "DENY")
    passed = rule in ("ELIGIBLE_WITH_PERSISTENCE_AND_PERFORMANCE", "ELIGIBLE_UNLESS_BLOCKED")
    return _outcome("DRIFT_SEVERITY_GATE", passed, "DRIFT_SEVERITY_INSUFFICIENT",
                    f"Severity {r.trigger_severity} is eligible under the frozen severity policy.",
                    f"Severity {r.trigger_severity} does not authorize retraining (frozen policy: {rule}).")


def _persistence_gate(r: RetrainingRequest, p: RetrainingPolicy, ctx):
    required = int(p.document["min_persistence_windows"])
    passed = r.persistence_window_count >= required
    return _outcome("DRIFT_PERSISTENCE_GATE", passed, "DRIFT_NOT_PERSISTENT",
                    f"Drift persisted for {r.persistence_window_count} windows (>= {required}).",
                    f"Drift persisted for only {r.persistence_window_count} windows (< {required}).")


def _performance_signal_gate(r: RetrainingRequest, p: RetrainingPolicy, ctx):
    conditions = p.document["performance_signal_rule"]["conditions"]
    detectors = set(r.trigger_detectors)
    severity_rank = SEVERITY_RANK.get(r.trigger_severity, 0)
    satisfied = strict = False
    # strict: a frozen condition fully satisfied. relaxed: satisfied except that the
    # persistence count is still short; the dedicated persistence gate then DEFERs.
    a = "PERFORMANCE_DRIFT" in detectors and r.persistence_window_count >= conditions["A"]["min_persistence_windows"]
    a_relaxed = "PERFORMANCE_DRIFT" in detectors
    b = ("ERROR_DISTRIBUTION_DRIFT" in detectors and r.persistence_window_count >= conditions["B"]["min_persistence_windows"]
         and severity_rank >= SEVERITY_RANK[conditions["B"]["min_severity"]])
    b_relaxed = "ERROR_DISTRIBUTION_DRIFT" in detectors and severity_rank >= SEVERITY_RANK[conditions["B"]["min_severity"]]
    c = ((detectors & {"FEATURE_DRIFT", "PREDICTION_DRIFT"}) and "PERFORMANCE_DRIFT" in detectors
         and r.persistence_window_count >= conditions["C"]["min_persistence_windows"] and r.mae_degradation_observed)
    c_relaxed = ((detectors & {"FEATURE_DRIFT", "PREDICTION_DRIFT"}) and "PERFORMANCE_DRIFT" in detectors
                 and r.mae_degradation_observed)
    d = bool(conditions["D"]["simulation_scenario"] and r.simulation_scenario_id
             and r.request_origin == "MANUAL_SIMULATION")
    strict = a or b or c or d
    relaxed = a_relaxed or b_relaxed or c_relaxed or d
    satisfied = strict or relaxed
    return _outcome("PERFORMANCE_SIGNAL_GATE", satisfied, "PERFORMANCE_EVIDENCE_INSUFFICIENT",
                    "A frozen performance-signal condition (A/B/C/D) is satisfied.",
                    "No frozen performance-signal condition authorizes retraining for this evidence.")


def _data_quality_gate(r: RetrainingRequest, p: RetrainingPolicy, ctx):
    policy = p.document["data_quality_policy"]
    passed = not (r.data_quality_critical and policy["critical_blocks_retraining"])
    return _outcome("DATA_QUALITY_GATE", passed, policy["reason_code"],
                    "No critical data-quality failure blocks this request.",
                    "Critical data-quality failure: corrupted data must not be trained on.")


def _label_gate(r: RetrainingRequest, p: RetrainingPolicy, ctx):
    return _outcome("LABEL_AVAILABILITY_GATE", r.labels_available, "LABELS_NOT_AVAILABLE",
                    "Labels are observable at or before the label availability cutoff.",
                    "Required labels are not yet available at the label availability cutoff.")


def _min_data_gate(r: RetrainingRequest, p: RetrainingPolicy, ctx):
    required = int(p.document["minimum_new_labeled_samples"])
    passed = r.new_labeled_sample_count >= required
    return _outcome("MINIMUM_NEW_DATA_GATE", passed, "INSUFFICIENT_NEW_DATA",
                    f"New labeled samples {r.new_labeled_sample_count} >= required {required}.",
                    f"New labeled samples {r.new_labeled_sample_count} < required {required}.")


def _cooldown_gate(r: RetrainingRequest, p: RetrainingPolicy, ctx):
    if ctx is None or not ctx.last_successful_job_end:
        return _outcome("COOLDOWN_GATE", True, "RETRAINING_COOLDOWN_ACTIVE", "No cooldown active.", "")
    hours = float(p.document["cooldown_hours"])
    elapsed = (datetime.fromisoformat(r.request_timestamp) - datetime.fromisoformat(ctx.last_successful_job_end)).total_seconds() / 3600.0
    active = elapsed < hours
    return _outcome("COOLDOWN_GATE", not active, "RETRAINING_COOLDOWN_ACTIVE",
                    f"Elapsed {elapsed:.1f}h since the last successful job (>= {hours:.0f}h cooldown).",
                    f"Elapsed {elapsed:.1f}h since the last successful job (< {hours:.0f}h cooldown).")


def _reference_state_gate(r: RetrainingRequest, p: RetrainingPolicy, ctx):
    passed = r.reference_state in p.document["allowed_reference_states"]
    return _outcome("REFERENCE_STATE_GATE", passed, "REFERENCE_STATE_INVALID",
                    f"Reference lifecycle state {r.reference_state} may serve as retraining source.",
                    f"Reference lifecycle state {r.reference_state} may not serve as retraining source.")


def _lineage_gate(r: RetrainingRequest, p: RetrainingPolicy, ctx):
    return _outcome("LINEAGE_GATE", r.lineage_status == "COMPLETE", "LINEAGE_INCOMPLETE",
                    "Required dataset-to-registry lineage is complete.",
                    "Required lineage for the retraining request is incomplete.")


def _model_fingerprint_gate(r: RetrainingRequest, p: RetrainingPolicy, ctx):
    expected = ctx.expected_model_fingerprint if (ctx and ctx.expected_model_fingerprint) else r.reference_model_fingerprint
    passed = r.reference_model_fingerprint == expected
    return _outcome("MODEL_FINGERPRINT_GATE", passed, "MODEL_FINGERPRINT_MISMATCH",
                    "Reference model fingerprint matches the frozen registry entry.",
                    "Reference model fingerprint differs from the frozen registry entry.")


def _feature_fingerprint_gate(r: RetrainingRequest, p: RetrainingPolicy, ctx):
    passed = r.actual_feature_fingerprint == r.expected_feature_fingerprint
    return _outcome("FEATURE_FINGERPRINT_GATE", passed, "FEATURE_FINGERPRINT_MISMATCH",
                    "Feature fingerprint matches the frozen specification.",
                    "Feature fingerprint differs from the frozen specification.")


def _protocol_gate(r: RetrainingRequest, p: RetrainingPolicy, ctx):
    passed = r.protocol_hash in p.document["accepted_protocol_hashes"]
    return _outcome("PROTOCOL_GATE", passed, "PROTOCOL_MISMATCH",
                    "Protocol hash is accepted by the frozen retraining policy.",
                    "Protocol hash is not accepted by the frozen retraining policy.")


def _final_test_gate(r: RetrainingRequest, p: RetrainingPolicy, ctx):
    passed = not r.requests_final_test_access
    return _outcome("FINAL_TEST_POLICY_GATE", passed, "FINAL_TEST_POLICY_VIOLATION",
                    "No final-test data access requested.",
                    "Phase 15 forbids retraining on or evaluating against final-test data.")


def _concurrency_gate(r: RetrainingRequest, p: RetrainingPolicy, ctx):
    passed = not r.job_already_running
    return _outcome("JOB_CONCURRENCY_GATE", passed, "RETRAINING_ALREADY_RUNNING",
                    "No retraining job is already running for this target and stream.",
                    "A retraining job is already running for this target and stream.")


GATES = (_policy_version_gate, _origin_gate, _evidence_gate, _severity_gate, _persistence_gate,
         _performance_signal_gate, _data_quality_gate, _label_gate, _min_data_gate, _cooldown_gate,
         _reference_state_gate, _lineage_gate, _model_fingerprint_gate, _feature_fingerprint_gate,
         _protocol_gate, _final_test_gate, _concurrency_gate)


class EvaluationContext:
    """Deterministic context: known evidence IDs, registry fingerprint, cooldown and job state."""
    def __init__(self, *, known_event_ids: set[str] | None = None, trusts_evidence: bool = False,
                 expected_model_fingerprint: str | None = None,
                 last_successful_job_end: str | None = None, prior_decisions: list[dict] | None = None):
        self.known_event_ids = known_event_ids or set()
        self.trusts_evidence = trusts_evidence
        self.expected_model_fingerprint = expected_model_fingerprint
        self.last_successful_job_end = last_successful_job_end
        self.prior_decisions = prior_decisions or []


def evaluate_request(request: RetrainingRequest, policy: RetrainingPolicy,
                     context: EvaluationContext | None = None) -> RetrainingDecision:
    if context is not None and context.prior_decisions:
        existing = find_existing_decision(context.prior_decisions, request.retraining_request_fingerprint)
        if existing is not None:
            return RetrainingDecision(
                request_id=request.request_id, target=request.target, decision=existing["decision"],
                reason_codes=[*existing["reason_codes"], "DUPLICATE_REQUEST"],
                gate_results=existing["gate_results"], policy_id=policy.policy_id,
                policy_version=policy.version, policy_checksum=policy.checksum,
                retraining_policy_fingerprint=policy.retraining_policy_fingerprint,
                evidence_refs=list(request.evidence_refs), data_cutoff=request.data_cutoff_timestamp,
                label_cutoff=request.label_availability_cutoff,
                training_window=existing.get("training_window"),
                retraining_request_fingerprint=request.retraining_request_fingerprint,
                simulation_scenario_id=request.simulation_scenario_id)
    outcomes = [fn(request, policy, context) for fn in GATES]
    blocking = [o for o in outcomes if not o.passed]
    defer_reasons = {"DRIFT_NOT_PERSISTENT", "LABELS_NOT_AVAILABLE", "INSUFFICIENT_NEW_DATA",
                     "RETRAINING_COOLDOWN_ACTIVE", "RETRAINING_ALREADY_RUNNING"}
    hard_fail = [o for o in blocking if o.reason_code not in defer_reasons]
    if hard_fail:
        decision = "DENY"; reasons = [o.reason_code for o in blocking]
    elif blocking:
        decision = "DEFER"; reasons = [o.reason_code for o in blocking]
    else:
        decision = "ALLOW"; reasons = ["RETRAINING_ALLOWED"]
    window = request.proposed_training_window if decision == "ALLOW" else None
    return RetrainingDecision(
        request_id=request.request_id, target=request.target, decision=decision, reason_codes=reasons,
        gate_results=[o.to_dict() for o in outcomes], policy_id=policy.policy_id,
        policy_version=policy.version, policy_checksum=policy.checksum,
        retraining_policy_fingerprint=policy.retraining_policy_fingerprint,
        evidence_refs=list(request.evidence_refs), data_cutoff=request.data_cutoff_timestamp,
        label_cutoff=request.label_availability_cutoff, training_window=window,
        retraining_request_fingerprint=request.retraining_request_fingerprint,
        simulation_scenario_id=request.simulation_scenario_id)
