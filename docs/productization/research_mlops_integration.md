# Research → MLOps integration

Stage 1 productization: connect the frozen 20-phase forecasting research pipeline to the MLOps layer through a single read-only integration adapter. The adapter emits real instances of the existing MLOps schemas (`MonitoringEvent`, `ResearchRegistry`, `GovernanceDecision`, `ChampionRegistry` snapshot) so that the forecasting system can be observed, evaluated, and lifecycle-controlled through the same deterministic governance as the research pipeline.

The integration is **read-only with respect to all Phase 19 evidence**. The five critical safety tests from the spec pass deterministically.

---

## 1. Current architecture

The repository is a 20-phase research project for energy forecasting on RTS-GMLC 2020. Each phase froze its artefacts before the next phase was allowed to read them. The architecture layers, with the actual modules that implement them:

| Layer | Module |
| --- | --- |
| Forecasting models | `src/smartgrid_mlops/models/`, `src/smartgrid_mlops/finalists/` |
| Predictions (frozen) | `artifacts/research_tables/final_predictions.csv` (13,176 rows) |
| Final metrics (frozen) | `artifacts/research_tables/final_forecasting_results.csv`, `final_model_comparison.csv` |
| Model artifact registry | `src/smartgrid_mlops/mlops/registry.py` (`ResearchRegistry`) |
| Lifecycle registry | `artifacts/model_registry/lifecycle_registry.yaml` |
| Monitoring (PSI / KS / rolling MAE) | `src/smartgrid_mlops/monitoring/` |
| Drift detection (events) | `src/smartgrid_mlops/monitoring/events.py` |
| Governance engine | `src/smartgrid_mlops/governance/` (13-state machine + deterministic gates) |
| Champion / challenger | `src/smartgrid_mlops/champion_challenger/registry.py` |
| Rollback | `src/smartgrid_mlops/agents/governance_agent.py` + governance transitions |
| Bounded agentic layer | `src/smartgrid_mlops/agents/` (drift, performance, security, governance, redteam) |
| Governance firewall | `src/smartgrid_mlops/agents/firewall.py` |
| Evidence ledger | `artifacts/mlops/audit/events.jsonl` |
| MLflow lineage | `artifacts/mlflow/` |
| Final evaluation (frozen) | `artifacts/experiments/final_evaluation/phase_19/official/` |

The productization layer is `src/smartgrid_mlops/productization/`, with `forecasting_to_mlops.py` as the single integration entry point.

## 2. Forecasting → MLOps data flow

The integration adapter reads the frozen Phase 19 evidence and emits real instances of the existing MLOps schemas. The data flow is:

```
artifacts/research_tables/final_forecasting_results.csv
artifacts/research_tables/final_model_comparison.csv
artifacts/research_tables/final_predictions.csv
artifacts/model_registry/forecasting_reference_registry.yaml
artifacts/model_registry/lifecycle_registry.yaml
artifacts/experimental_design/phase_10_ablation_protocol_freeze.yaml
            │
            ▼
   smartgrid_mlops.productization.forecasting_to_mlops
            │
            ├── ForecastingModelRecord  →  ResearchRegistry entries
            ├── MonitoringEvent records  →  existing monitoring.events schema
            ├── ChampionRegistry snapshot (additive, simulation-scoped)
            └── GovernanceDecision  →  existing GovernanceEngine with the
                                       frozen Phase 13 policy
```

The adapter writes **nothing** under `artifacts/`, `config/`, `data/`, `reports/`, or `src/smartgrid_mlops/` (other than its own module file). The Phase 19 evidence is read-only.

## 3. Model artifact interface

Each `ForecastingModelRecord` (see `src/smartgrid_mlops/productization/forecasting_to_mlops.py`) is a real, deterministic projection of a frozen finalist into the existing MLOps schema. The fields mirror the existing `ResearchRegistry.REQUIRED` set exactly, so the records can be registered without inventing a duplicate lifecycle. Per target:

| Target | Model | Implementation ID | Final MAE | Benchmark | Δ relative |
| --- | --- | --- | ---: | --- | ---: |
| load | random_forest | RANDOM_FOREST | 174.26 | RTS_DAY_AHEAD 101.14 | +72.29% |
| wind | hist_gradient_boosting | HIST_GRADIENT_BOOSTING | 778.84 | RTS_DAY_AHEAD 331.30 | +135.08% |
| pv | random_forest | RANDOM_FOREST | 36.12 | H24_DAILY_PERSISTENCE 39.09 | −7.61% |

The records reuse the frozen registry IDs (`MLOPS-REF-{TARGET}-H24-V1`) and the frozen lifecycle states (`REGISTERED_REFERENCE`) from the existing Phase 13 lifecycle registry. There is no duplicate model representation.

## 4. Registry integration

The productization adapter uses the existing `ResearchRegistry.register()` method. The `to_registry_entry()` projection of each `ForecastingModelRecord` satisfies every field in `ResearchRegistry.REQUIRED`, so the records are directly registerable. The integration does **not** mutate the existing `lifecycle_registry.yaml` or the existing `forecasting_reference_registry.yaml`. The productization projection is a *view*, not a new model representation.

For the champion-challenger layer, the integration produces a snapshot that can be loaded into the existing `ChampionRegistry` (`src/smartgrid_mlops/champion_challenger/registry.py`) as an additive record. The champion registry is already additive and simulation-scoped; the productization snapshot respects that contract.

## 5. Monitoring architecture

The productization layer uses the existing `monitoring.events.make_event` schema to emit one `MonitoringEvent` per target per evidence type. The four event types are:

| Event type | Count | Evidence |
| --- | --- | --- |
| `performance_evaluation` | 1 per target | development MAE, final-test MAE, benchmark MAE, degradation percent |
| `prediction_distribution` | 2 per target (frozen + benchmark) | mean / P95 / max absolute error over the 1464-row final-test window |
| `model_health` | 1 per target | artifact digest, health status (`AVAILABLE` / `UNAVAILABLE`) |

Total: 12 events. No new monitoring layer is invented; the productization reuses the existing event schema so downstream consumers do not need a second adapter.

The PSI / KS / rolling-MAE / prediction-drift detectors in `src/smartgrid_mlops/monitoring/` are the existing implementation. The productization layer does not implement new monitoring metrics; it only emits structured events over the existing metrics.

## 6. Agent architecture

The productization layer uses the **existing** bounded agent layer unchanged. It does not create new agents. The 5 agents in `src/smartgrid_mlops/agents/` (drift, performance, security, governance, redteam) are invoked through the existing `Orchestrator` (`agents/orchestrator.py`), and every recommendation passes the existing governance firewall (`agents/firewall.py`).

The integration is wired so the agent layer can RECOMMEND but cannot MUTATE. The `run_safety_integration` entry point exercises a real bounded-agent query (`EXPLAIN_DRIFT`) through the orchestrator, observing that the agent emits only `AGENT_RECOMMENDATION_CREATED` events and never any lifecycle mutation.

## 7. Agent authority boundary

The boundary is enforced by the existing governance firewall (`agents/firewall.py`). The firewall returns `ALLOW` only for advisory types: `INVESTIGATE / SUMMARIZE / EXPLAIN / REQUEST_HUMAN_REVIEW / CREATE_REPORT`. Lifecycle action types are blocked:

- `PROMOTE` → blocked (`UNKNOWN_RECOMMENDATION_BLOCKED` or `UNSAFE_RECOMMENDATION_BLOCKED`)
- `DEPLOY` → blocked
- `ROLLBACK` → blocked
- `RETRAIN` → blocked
- `CHANGE_POLICY` → blocked (`UNSAFE_RECOMMENDATION_BLOCKED`)
- `MODIFY_MODEL` → blocked
- `MODIFY_FEATURES` → blocked

The boundary is **not** enforced by a system prompt alone. It is enforced at the firewall level (deny-by-default) and at the governance level (the `GovernanceEngine` refuses transitions that violate the frozen policy). The forbidden audit events `AGENT_MODEL_PROMOTED` and `AGENT_RETRAINING_STARTED` cannot be emitted by construction.

## 8. Governance architecture

The productization layer uses the existing `GovernanceEngine` (`src/smartgrid_mlops/governance/policy_engine.py`) and the existing `GovernancePolicy.load()` (which loads the frozen Phase 13 policy at `config/governance/phase_13_policy.yaml`). The 13-state lifecycle and deterministic gates are reused unchanged.

The `build_governance_decision()` function is a thin wrapper that constructs the existing `CandidateContext` and `TransitionRequest` and calls `engine.evaluate()`. Decisions are deterministic: identical inputs (subject_id, current_state, proposed_state, candidate context, policy) produce identical `GovernanceDecision` objects with identical `decision_content_fingerprint`.

## 9. Retraining flow

The retraining flow is the existing Phase 15 governed retraining pipeline (`src/smartgrid_mlops/retraining/`). The productization layer does not implement new retraining logic. When monitoring surfaces a performance or drift signal, the existing supervisor (`src/smartgrid_mlops/supervisor/supervisor.py`) issues a `RETRAIN` decision through the same governance pipeline; the productization layer observes the result via the evidence ledger and does not interfere.

## 10. Champion / challenger flow

The productization layer produces a `ChampionRegistry` snapshot from the frozen forecasting evidence (three REFERENCE models, one per target). The snapshot is a structured record (a dict with `mode: SIMULATION`, `champions: {target: ...}`, `preserved_models: [...]`). It is compatible with the existing `ChampionRegistry.load(path).record_promotion()` / `record_rollback()` / `record_preservation()` API.

The productization does not create new lifecycle states or transition rules. Promotion, rollback, and canary transitions are exclusively the responsibility of the existing `GovernanceEngine.evaluate()`.

## 11. Rollback flow

Rollback is implemented through the existing governance `ROLLBACK_REQUIRED` lifecycle state and the existing `GovernanceEngine` rollback requirements (policy file: `config/governance/phase_13_policy.yaml`, `rollback_requirements` section). The productization layer exposes a single function `build_governance_decision()` that can be called with `current_state="ACTIVE", proposed_state="ARCHIVED"` (or any other valid transition) and the engine returns the deterministic decision. The ChampionRegistry snapshot records `preserved_models` for restoration, and the existing champion-challenger `rollback()` method is reusable.

Every transition produces a real `GovernanceDecision` (with `decision_id`, `timestamp`, `decision_content_fingerprint`) and the existing evidence ledger is appended to.

## 12. Evidence / audit flow

The productization layer appends to the existing evidence ledger at `artifacts/mlops/audit/events.jsonl` through the existing `mlops.audit.append_audit_event` API. The `MonitoringEvent` records emitted by the productization layer carry the same `event_id` and `timestamp` format as the existing monitoring events.

For lifecycle decisions, the existing `GovernanceEngine` produces a `GovernanceDecision` object with a `decision_content_fingerprint` (sha256 over canonical content). The productization layer's safety integration exercises this end-to-end.

## 13. Existing reusable components

The productization layer reuses the following existing components without modification:

| Component | Reused as |
| --- | --- |
| `mlops.registry.ResearchRegistry` | Target for `ForecastingModelRecord.to_registry_entry()` |
| `monitoring.events.make_event` | Schema for monitoring signals |
| `monitoring.feature_drift.psi` / `normalized_wasserstein` | Drift detection (reused indirectly through the existing pipeline) |
| `monitoring.performance_drift.rolling_mae` | Performance drift (reused indirectly) |
| `governance.policy_engine.GovernanceEngine` | All transition decisions |
| `governance.policies.GovernancePolicy.load()` | Frozen policy loader |
| `governance.schemas.{LIFECYCLE_STATES, CandidateContext, TransitionRequest, GovernanceDecision}` | Decision schema |
| `agents.orchestrator.Orchestrator` | Bounded agent execution |
| `agents.firewall.firewall_validate` | Lifecycle action block |
| `champion_challenger.registry.ChampionRegistry` | Champion / challenger additive records |
| `mlops.audit.append_audit_event` | Append-only audit ledger |

## 14. Missing integration points

Before Stage 2 (the API service layer) the productization has no missing integration points for the spec. It exposes:

- `build_forecasting_records(root)` — deterministic records
- `build_monitoring_signals(records, root)` — structured events
- `build_champion_challenger_snapshot(records, root)` — additive snapshot
- `build_governance_decision(root, ...)` — single transition evaluation
- `run_safety_integration(root)` — the five spec safety tests as a single call

## 15. Required adapters

The productization layer adds exactly one new module: `src/smartgrid_mlops/productization/forecasting_to_mlops.py`. The `__init__.py` re-exports the public functions. No adapters are duplicated: the existing `ResearchRegistry`, `GovernanceEngine`, `Orchestrator`, and `ChampionRegistry` are used directly.

## 16. Testing strategy

`tests/test_productization_safety.py` (20 tests) covers:

- **Forecasting records**: three records, one per target; values match the frozen evidence; all required fields are present; deterministic.
- **Monitoring signals**: 12 events (3 targets × 4 event types); schema matches the existing `monitoring.events` layer.
- **Champion / challenger snapshot**: three champions; preserved models subset of the existing lifecycle registry.
- **Governance determinism**: identical inputs produce identical decisions; 13 lifecycle states (matches the existing implementation).
- **Five critical safety tests** (spec section 10): unsafe promotion blocked, unsafe rollback blocked, missing evidence blocked, policy conflict overridden, agent cannot mutate lifecycle.
- **Non-goals**: no quantum / QML / GNN / LLM claims in the productization module.
- **No artefact mutation**: ten Phase 19 artefacts are SHA-256 verified before and after the integration runs.

## 17. Future experimental design

The productization layer supports the three experimental configurations from the spec without any code changes:

### A. Traditional deterministic MLOps
```
Monitoring → Rules → Lifecycle
```
The productization layer emits the same `MonitoringEvent` records that the existing `monitoring.events` layer already consumes. The deterministic governance pipeline (`GovernanceEngine`) can consume the events directly.

### B. Agent-assisted MLOps
```
Monitoring → Agent → Recommendation → Controlled lifecycle
```
The productization layer's bounded `Agent` layer (via the existing `Orchestrator`) produces structured recommendations. The orchestrator's firewall blocks lifecycle mutations; the agent's advisory outputs are surfaced to the operator.

### C. Agentic MLOps + deterministic governance
```
Monitoring → Agentic analysis → Recommendation → Governance firewall → Lifecycle
```
This is the active configuration. The productization layer exercises it through `run_safety_integration`, which runs the five critical safety tests.

### Measurable outcomes (where legitimately measurable)

- **Detection latency** — derivable from the existing `monitoring.windows.make_windows` + severity classifier (not invented here).
- **Blocked unsafe actions** — measured: 7 of 7 lifecycle action types blocked by the firewall; 4 of 4 unsafe governance requests denied by the deterministic engine.
- **Governance violations prevented** — measured by the spec safety tests.
- **Recommendation accuracy** — measured by the existing Phase 18 ablation (8/8 agent quality probes passed; ~72% explanation-effort reduction under a frozen cost model).

We do **not** invent new metrics that are not already measured by the existing system. The productization layer does not add or alter metric definitions.

## 18. Product API implications

The productization layer exposes a stable Python API for Stage 2 (the API service layer). The API is read-only and deterministic:

```python
from smartgrid_mlops.productization import (
    build_forecasting_records,
    build_monitoring_signals,
    build_champion_challenger_snapshot,
    build_governance_decision,
    run_safety_integration,
)

records = build_forecasting_records(Path("."))
signals = build_monitoring_signals(records, Path("."))
snap = build_champion_challenger_snapshot(records, Path("."))
decision = build_governance_decision(Path("."), subject_id="...", current_state="PROMOTION_ELIGIBLE",
                                     proposed_state="APPROVAL_PENDING", actor_type="AGENT", simulation=True)
safety = run_safety_integration(Path("."))
```

The API consumes a `Path` (the project root) and emits Python dataclasses / dicts. Stage 2 should expose this as a thin FastAPI surface; the productization API is the contract.

## 19. Explicit non-goals

> **Quantum computing and Quantum Machine Learning are not part of this project.**

The productization layer does not add or use:

- Quantum computing (Qiskit, PennyLane, Cirq, QML, qubits, ansatz, VQC)
- Graph neural networks (GNN, graph-native representations)
- Large language models (no LLM is invoked at runtime; the `LLMBackendInterface` is documented as a contract only)
- New metric definitions
- New lifecycle states
- New audit events
- Modifications to any frozen research artefact

These constraints are enforced in `tests/test_productization_safety.py::TestNonGoals` and `tests/test_productization_safety.py::TestNoArtefactMutation`.

---

The Stage 1 productization layer is complete. The next stage consumes this interface to expose the API service layer.
