# Guardrailed Agentic MLOps — FastAPI service

Thin FastAPI service over the existing research + MLOps layer. Read-only and advisory-only. The service is an **interface layer** — it does not re-implement forecasting, monitoring, drift detection, agent reasoning, governance, the model registry, retraining, champion/challenger, rollback, or audit logging.

It exposes the Stage 1 productization contract (`src/smartgrid_mlops/productization/`) over HTTP, with no business logic of its own.

## Project context

This is the Stage 2 deliverable of a 20-phase research project (`Guardrailed Agentic MLOps for Self-Adaptive Energy Forecasting in Renewable-Integrated Smart Grids`). The research is complete. The final evaluation is frozen. This service is the API layer for the completed research artefact.

## Architecture

```
FastAPI (this package: product/backend_api/app/)
        ↓
Productization Contract (src/smartgrid_mlops/productization/)
        ↓
Existing research implementation
   - mlops.registry.ResearchRegistry
   - monitoring.events.make_event
   - governance.policy_engine.GovernanceEngine
   - governance.policies.GovernancePolicy
   - agents.orchestrator.Orchestrator + agents.firewall.firewall_validate
   - champion_challenger.registry.ChampionRegistry
   - mlops.audit.append_audit_event + read_audit_events
   - research artefacts (artifacts/research_tables/, artifacts/model_registry/, etc.)
```

The service contains NO business logic. Every endpoint delegates to the existing implementation.

## Endpoints (17 total)

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | API + research + productization health |
| GET | `/api/forecasts` | Per-target forecast info (3 records) |
| GET | `/api/forecasts/{target}` | One forecast info (load / wind / pv) |
| GET | `/api/forecasts/{target}/metrics` | 5-metric result (MAE, RMSE, sMAPE, nMAE, nRMSE) |
| GET | `/api/forecasts/{target}/predictions` | Per-row frozen predictions |
| GET | `/api/models` | Existing research registry (3 reference entries) |
| GET | `/api/models/{model_id}` | One registry entry |
| GET | `/api/monitoring/events` | 12 productization monitoring events |
| GET | `/api/monitoring/events/{event_id}` | One event |
| GET | `/api/monitoring/drift` | Drift-prefixed events |
| GET | `/api/governance/policy` | Frozen Phase 13 policy |
| POST | `/api/governance/decisions` | Evaluate a single transition |
| GET | `/api/governance/decisions` | Existing decision log (JSONL) |
| GET | `/api/agents/types` | Bounded agent query types (advisory only) |
| POST | `/api/agents/explain` | Bounded agent explanation (advisory, firewall-validated) |
| GET | `/api/audit/events` | Existing evidence-ledger events |
| GET | `/api/audit/verify` | Existing ledger JSONL well-formed check |

See `/docs` (Swagger UI), `/redoc`, or `/openapi.json` for full schemas.

## Safety guarantees

- 7/7 lifecycle action types (`PROMOTE`, `DEPLOY`, `ROLLBACK`, `RETRAIN`, `CHANGE_POLICY`, `MODIFY_MODEL`, `MODIFY_FEATURES`) are blocked by the existing agent firewall (`smartgrid_mlops.agents.firewall.firewall_validate`).
- The OpenAPI schema is asserted by the test suite to contain NO path with `promote`, `deploy`, `rollback`, `retrain`, `change_policy`, `modify`, or `approve_deployment` suffixes.
- The Stage 1 `run_safety_integration` entry point is re-executed by the Stage 2 test suite and must still report `ALL_SAFETY_TESTS_PASSED`.

## Offline limitations

The API is **read-only** and the underlying system is **offline evaluation**:

- No live monitoring, no streaming, no real-time telemetry.
- The productization layer's monitoring events are derived from a one-shot read of the frozen final-test evidence.
- The agent layer is local-rule-based; no LLM is invoked at runtime.
- The audit ledger is the existing Phase 13 JSONL file.

## Installation

The project root already contains a working `pip` install. To extend with API dependencies:

```bash
.venv/Scripts/python.exe -m pip install fastapi uvicorn httpx
```

## Running the API (development)

```bash
cd C:/Projects/guardrailed-agentic-mlops-smart-grid_trial
.venv/Scripts/python.exe -m uvicorn product.backend_api.app.main:app --reload
```

Then open <http://127.0.0.1:8000/docs>.

## Running the API (production)

```bash
cd C:/Projects/guardrailed-agentic-mlops-smart-grid_trial
.venv/Scripts/python.exe -m uvicorn product.backend_api.app.main:app --host 0.0.0.0 --port 8000 --workers 1
```

Set `SMARTGRID_MLOPS_PROJECT_ROOT` if the API process is started outside the repository.

## Testing

```bash
cd C:/Projects/guardrailed-agentic-mlops-smart-grid_trial
.venv/Scripts/python.exe -m pytest tests/test_api_service.py -v
```

The test suite (29 tests) verifies:

- All 17 endpoints respond with the expected schema
- 7/7 lifecycle action types are blocked by the firewall
- The OpenAPI schema contains no lifecycle mutation paths
- The Stage 1 `run_safety_integration` still reports `ALL_SAFETY_TESTS_PASSED`
- No protected research artefact is mutated by any API call
- The API module contains no quantum / QML / GNN / LLM claims

## Project root resolution

The package resolves the project root at startup in this order:

1. `SMARTGRID_MLOPS_PROJECT_ROOT` environment variable (if set)
2. The default: 3 directories up from this `__init__.py`'s location (i.e. `product/backend_api/app/` -> `product/backend_api/` -> `product/` -> project root)

## Out of scope

- Frontend (the spec defers this to Stage 3)
- Authentication (no existing architecture requires it)
- Caching, message queues, distributed deployment
- Live model serving
- LLM-backed agents
- Quantum / QML / GNN
- Mutation endpoints (governed lifecycle transitions remain the responsibility of the existing research pipeline)

## Files

```
product/backend_api/
├── README.md
└── app/
    ├── __init__.py
    ├── main.py             # FastAPI app factory + middleware
    ├── config.py           # project root resolution
    ├── dependencies.py     # AppState singleton (Stage 1 productization records + signals + snapshot)
    ├── schemas.py          # Pydantic v2 request/response models
    ├── routers/
    │   ├── health.py       # GET /health
    │   ├── forecasts.py    # /api/forecasts*
    │   ├── models.py       # /api/models*
    │   ├── monitoring.py   # /api/monitoring*
    │   ├── governance.py   # /api/governance*
    │   ├── agents.py       # /api/agents*
    │   └── audit.py        # /api/audit*
    └── services/           # Reserved; intentionally empty (no service-layer files)
```

The corresponding test suite is in `tests/test_api_service.py`.
