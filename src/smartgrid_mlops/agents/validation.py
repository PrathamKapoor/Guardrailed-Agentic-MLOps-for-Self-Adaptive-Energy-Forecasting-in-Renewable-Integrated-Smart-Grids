"""Phase 17 guardrails: output contract, structured-evidence-only inputs,
final-test denial, no forbidden audit events."""
from __future__ import annotations
from .schemas import (AGENT_AUDIT_EVENT_TYPES, FINAL_TEST_MARKERS, FORBIDDEN_AUDIT_EVENT_TYPES,
                      OUTPUT_CONTRACT_FIELDS)


def assert_valid_output(output: dict) -> None:
    missing = [f for f in OUTPUT_CONTRACT_FIELDS if f not in output or output[f] in (None, "")]
    if missing:
        raise ValueError(f"AGENT_OUTPUT_CONTRACT_VIOLATION: missing {missing}")
    if not 0.0 <= float(output["confidence"]) <= 1.0:
        raise ValueError("AGENT_OUTPUT_CONTRACT_VIOLATION: confidence must be advisory in [0, 1]")


def assert_structured_evidence(evidence: dict) -> None:
    """Agents receive structured evidence objects only — never raw filesystem access."""
    if not isinstance(evidence, dict):
        raise ValueError("AGENT_INPUT_CONTRACT_VIOLATION: evidence must be a structured mapping")


def assert_no_final_test_access(value=None) -> None:
    if value and any(x in str(value).lower() for x in FINAL_TEST_MARKERS):
        raise ValueError("AGENT_FINAL_TEST_ACCESS_BLOCKED")


def assert_no_forbidden_agent_events(event_types) -> None:
    for event_type in event_types:
        if event_type in FORBIDDEN_AUDIT_EVENT_TYPES:
            raise ValueError(f"FORBIDDEN_AGENT_EVENT: {event_type}")
        if event_type not in AGENT_AUDIT_EVENT_TYPES:
            raise ValueError(f"UNKNOWN_AGENT_EVENT: {event_type}")
