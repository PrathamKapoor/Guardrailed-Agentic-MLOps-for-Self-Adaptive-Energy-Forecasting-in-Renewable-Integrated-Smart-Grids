"""Pydantic v2 schemas for the API.

Every field is taken from the Stage 1 productization contract or the
existing research artefacts. No new fabricated fields."""
from __future__ import annotations
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ---------------- Forecasts ----------------

class ForecastMetric(BaseModel):
    target: str
    model: str
    features: str
    mae: float
    rmse: float
    smape: float
    nmae: float
    nrmse: float


class ForecastSample(BaseModel):
    timestamp: str
    target: str
    model: str
    prediction: float
    actual: float
    absolute_error: float


class ForecastInfo(BaseModel):
    target: str
    model: str
    framework: str
    feature_set: str
    feature_count: int
    horizon: int
    n_samples: int
    final_test_mae: float
    final_test_benchmark_mae: float
    final_test_relative_difference_pct: float
    final_test_status: str
    strongest_benchmark: str
    development_mae: float


# ---------------- Model Registry ----------------

class ModelRecord(BaseModel):
    registry_id: str
    target: str
    horizon: int
    research_role: str
    registry_state: str
    lifecycle_state: str
    model_family: str
    framework: str
    implementation_id: str
    model_spec_fingerprint: str
    feature_set_id: str
    feature_spec_fingerprint: str
    dataset_fingerprint: str
    protocol_hash: str
    development_primary_metric: str
    development_mae: float
    strongest_benchmark: str
    benchmark_mae: float
    development_benchmark_gate: str
    evidence_status: str
    selection_evidence: str
    created_from_phase: int
    final_test_performance_status: str


# ---------------- Monitoring ----------------

class MonitoringEvent(BaseModel):
    event_id: str
    timestamp: str
    event_type: str
    target: str
    model: str
    extra: dict = Field(default_factory=dict, description="All additional event fields")


# ---------------- Governance ----------------

class PolicyInfo(BaseModel):
    policy_id: str
    policy_version: str
    policy_checksum: str
    governance_policy_fingerprint: str
    lifecycle_states: list[str]
    reason_codes: list[str]
    source_path: str


class GovernanceDecisionRecord(BaseModel):
    decision_id: str
    subject_id: str
    requested_transition: str
    decision: str
    current_state: str
    proposed_state: str
    policy_id: str
    policy_version: str
    policy_checksum: str
    reason_codes: list[str]
    explanation: str
    decision_content_fingerprint: str
    timestamp: str
    gate_results: list[dict] = Field(default_factory=list)
    actor_type: str
    simulation: bool


# ---------------- Agents ----------------

class AgentExplanationRequest(BaseModel):
    query: str = Field(..., description="User-facing question; advisory only.")
    context: dict = Field(default_factory=dict, description="Structured evidence keys: model, target, drift, performance, etc.")


class AgentExplanationResponse(BaseModel):
    agent_id: str
    agent_version: str
    query_id: str
    input_evidence_refs: list[str]
    reasoning_summary: str
    recommendation: str
    confidence: float
    limitations: str
    requires_human_review: bool
    timestamp: str
    firewall_decision: str
    firewall_reason_code: str


# ---------------- Audit ----------------

class AuditEvent(BaseModel):
    seq: Optional[int] = None
    timestamp: str
    type: str
    record: dict


class AuditChainVerification(BaseModel):
    chain_ok: bool
    message: str
    head: str


# ---------------- Health ----------------

class HealthStatus(BaseModel):
    status: str
    api: str
    research_pipeline: str
    productization: str
    artifacts: dict
    notes: list[str] = Field(default_factory=list)
