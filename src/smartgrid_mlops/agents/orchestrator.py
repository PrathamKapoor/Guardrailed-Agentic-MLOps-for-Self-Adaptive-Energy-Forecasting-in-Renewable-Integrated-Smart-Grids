"""Orchestrator: query -> agent analysis -> governance firewall -> memory + audit.

The only path from an agent to the outside world. Unsafe recommendation types
are blocked here; no agent output can execute, modify, train, deploy, or
alter anything. Advisory text from any LLM-style backend is carried as
UNTRUSTED text and never parsed into actions."""
from __future__ import annotations
from pathlib import Path
from . import audit as agent_audit
from .firewall import firewall_validate
from .memory import MemoryStore
from .planner import Planner
from .schemas import AgentOutput, AgentQuery
from .validation import assert_structured_evidence, assert_valid_output


class Orchestrator:
    def __init__(self, project_root: Path, audit_path: Path | None = None, memory_dir: Path | None = None):
        self.project_root = Path(project_root)
        self.audit_path = Path(audit_path) if audit_path else self.project_root / "artifacts/mlops/audit/events.jsonl"
        self.memory = MemoryStore(Path(memory_dir) if memory_dir
                                  else self.project_root / "artifacts/agents/phase_17/memory")
        self.planner = Planner(self.project_root)

    def handle(self, query: AgentQuery) -> dict:
        assert_structured_evidence(query.payload)
        agent_audit.emit(self.audit_path, "AGENT_QUERY_RECEIVED", query.query_id,
                         {"query_type": query.query_type})
        agent = self.planner.route(query.query_type)
        # An untrusted advisory recommendation (e.g., parsed from LLM text) may be
        # injected into the payload; the firewall decides whether it may pass.
        advisory = str(query.payload.get("advisory_recommendation_type", "") or "")
        output: AgentOutput = agent.analyze(query)
        if advisory:
            output.recommendation = advisory.strip().upper()
            output.advisory_text_untrusted = str(query.payload.get("advisory_text", ""))
        assert_valid_output(output.to_dict())
        agent_audit.emit(self.audit_path, "AGENT_ANALYSIS_COMPLETED", output.agent_id,
                         {"query_id": query.query_id, "agent_version": output.agent_version})
        if output.blocked:
            # blocked upstream by an evidence guard (e.g., final-test retrieval denial)
            firewall_result = {"allowed": False, "reason_code": output.block_reason,
                               "explanation": "Blocked before recommendation validation."}
            agent_audit.emit(self.audit_path, "AGENT_RECOMMENDATION_BLOCKED", output.agent_id,
                             {"query_id": query.query_id, "reason_code": output.block_reason})
        else:
            result = firewall_validate(output.recommendation)
            firewall_result = result.to_dict()
            if not result.allowed:
                output.blocked = True
                output.block_reason = result.reason_code
                agent_audit.emit(self.audit_path, "AGENT_RECOMMENDATION_BLOCKED", output.agent_id,
                                 {"query_id": query.query_id, "recommendation": output.recommendation,
                                  "reason_code": result.reason_code})
            else:
                agent_audit.emit(self.audit_path, "AGENT_RECOMMENDATION_CREATED", output.agent_id,
                                 {"query_id": query.query_id, "recommendation": output.recommendation,
                                  "requires_human_review": output.requires_human_review})
                if output.requires_human_review:
                    agent_audit.emit(self.audit_path, "HUMAN_REVIEW_REQUESTED", output.agent_id,
                                     {"query_id": query.query_id, "recommendation": output.recommendation})
        record = self.memory.store(output.memory_record(firewall_result))
        return {"output": output.to_dict(), "firewall": firewall_result, "memory_record": record}
