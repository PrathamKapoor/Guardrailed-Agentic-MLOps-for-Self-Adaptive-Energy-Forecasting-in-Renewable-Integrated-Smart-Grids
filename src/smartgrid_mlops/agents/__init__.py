"""Bounded agentic AI decision-support layer with governance firewall (Phase 17).

Agents explain, summarize, retrieve evidence, and prepare decision packets.
They never control the lifecycle: every recommendation passes the governance
firewall, and deterministic governance retains sole authority over promotion,
rollback, retraining, features, thresholds, and lifecycle transitions.
"""
from .schemas import AgentQuery, AgentOutput, ALLOWED_RECOMMENDATIONS, BLOCKED_RECOMMENDATIONS
from .firewall import firewall_validate

__all__ = ["AgentQuery", "AgentOutput", "ALLOWED_RECOMMENDATIONS", "BLOCKED_RECOMMENDATIONS", "firewall_validate"]
