"""Agent backend abstraction.

LOCAL_RULE_BASED is the default deterministic backend: explanations are
generated from structured evidence by fixed templates. An optional
LLM_BACKEND_INTERFACE exists for future research; its output is UNTRUSTED
ADVISORY TEXT that must pass the governance firewall and can never execute,
modify, train, deploy, or alter anything."""
from __future__ import annotations
from abc import ABC, abstractmethod


class AgentBackend(ABC):
    backend_type: str = "ABSTRACT"

    @abstractmethod
    def analyze(self, agent_id: str, query_type: str, evidence: dict) -> str:
        """Return advisory text. Rule-based backends return deterministic text;
        LLM backends return UNTRUSTED ADVISORY TEXT."""


class LocalRuleBackend(AgentBackend):
    """The authoritative backend. Deterministic, offline, no external API.

    This is the designed production path, not a placeholder for a missing
    LLM: project policy excludes non-deterministic model backends so that
    every agent output is reproducible and auditable. Specialized agent
    subclasses override analyze(); this base implementation is the
    deterministic fallback for agents that carry no template of their own.
    """
    backend_type = "LOCAL_RULE_BASED"

    def analyze(self, agent_id: str, query_type: str, evidence: dict) -> str:
        # Intentional deterministic fallback (see docstring): specialized
        # agents override this with their template logic.
        return ""


class LLMBackendInterface(AgentBackend):
    """Optional interface only. No implementation is provided or required.

    Contract for any future implementation:
    - output is UNTRUSTED ADVISORY TEXT, never executed or persisted as truth;
    - it cannot run commands, modify files, call training or deployment, or
      alter policies;
    - every derived recommendation must pass the governance firewall."""
    backend_type = "LLM_BACKEND_INTERFACE"

    def __init__(self, *args, **kwargs):
        raise NotImplementedError("No LLM backend is configured; the deterministic rule backend is authoritative")

    def analyze(self, agent_id: str, query_type: str, evidence: dict) -> str:
        raise NotImplementedError("No LLM backend is configured; the deterministic rule backend is authoritative")


class Agent:
    """Bounded specialist agent: structured evidence in, contract-conforming
    advisory output out. No filesystem, network, or lifecycle access."""
    agent_id: str = "AGENT"
    agent_version: str = "0.0.0"

    def __init__(self, backend: AgentBackend | None = None):
        self.backend = backend or LocalRuleBackend()

    def evidence_refs(self, evidence: dict) -> list[str]:
        return [str(x) for x in evidence.get("evidence_refs", [])]
