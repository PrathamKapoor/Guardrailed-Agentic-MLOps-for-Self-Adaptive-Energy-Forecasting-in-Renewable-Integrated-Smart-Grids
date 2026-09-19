"""Governance firewall: every agent recommendation passes through here.

Allowed advisory types (5): INVESTIGATE, SUMMARIZE, EXPLAIN, REQUEST_HUMAN_REVIEW,
CREATE_REPORT. Blocked lifecycle action types (7): PROMOTE, DEPLOY, ROLLBACK, RETRAIN,
CHANGE_POLICY, MODIFY_MODEL, MODIFY_FEATURES (plus synonyms and any unknown types)."""
from __future__ import annotations
from .schemas import ALLOWED_RECOMMENDATIONS, BLOCKED_RECOMMENDATIONS


class FirewallResult:
    def __init__(self, allowed: bool, reason_code: str, explanation: str):
        self.allowed = allowed
        self.reason_code = reason_code
        self.explanation = explanation

    def to_dict(self) -> dict:
        return {"allowed": self.allowed, "reason_code": self.reason_code, "explanation": self.explanation}


def firewall_validate(recommendation_type: str) -> FirewallResult:
    recommendation = (recommendation_type or "").strip().upper()
    if recommendation in ALLOWED_RECOMMENDATIONS:
        return FirewallResult(True, "RECOMMUNICATION_ALLOWED",
                              f"Advisory recommendation type {recommendation} is permitted; deterministic governance retains authority.")
    if recommendation in BLOCKED_RECOMMENDATIONS:
        return FirewallResult(False, "UNSAFE_RECOMMENDATION_BLOCKED",
                              f"Agent recommendation {recommendation} is a lifecycle action; agents cannot control lifecycle actions.")
    return FirewallResult(False, "UNKNOWN_RECOMMENDATION_BLOCKED",
                          f"Unknown recommendation type '{recommendation_type}' is blocked by default.")
