"""Stage 1 productization: connect frozen forecasting evidence to MLOps schemas.

This package is the integration adapter between the 20-phase research pipeline
and the MLOps layer. It reads the frozen Phase 19 evidence and emits real
instances of the existing MLOps schemas (MonitoringEvent, ResearchRegistry,
GovernanceDecision, ChampionRegistry entry) so that the forecasting system
can be observed, evaluated, and lifecycle-controlled through the same
deterministic governance as the research pipeline.

Strict constraints (from the spec):

* No quantum / QML / GNN / LLM claims or additions.
* Read-only with respect to the frozen Phase 19 artefacts.
* Reuse existing modules; add adapters, do not duplicate.
* The agent cannot mutate lifecycle state; the firewall is the same one
  used by Phase 17.
* The five critical safety tests live in tests/test_productization_safety.py.
"""
from .forecasting_to_mlops import (
    ForecastingModelRecord,
    build_forecasting_records,
    build_monitoring_signals,
    build_champion_challenger_snapshot,
    build_governance_decision,
    run_safety_integration,
)

__all__ = [
    "ForecastingModelRecord",
    "build_forecasting_records",
    "build_monitoring_signals",
    "build_champion_challenger_snapshot",
    "build_governance_decision",
    "run_safety_integration",
]
