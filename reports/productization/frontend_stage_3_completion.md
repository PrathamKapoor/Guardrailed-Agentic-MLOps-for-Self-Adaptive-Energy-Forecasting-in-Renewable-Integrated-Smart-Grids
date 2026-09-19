# Frontend dashboard (Stage 3) — completion report

## Phase status

**STAGE 3 COMPLETE — frontend dashboard consumes the Stage 2 FastAPI service.**
No model files, no research artefacts, no governance state, no protocol hashes, no
agent permissions were modified. The Stage 1 safety guarantee is preserved end-to-end
(7/7 lifecycle action types blocked, Stage 1 `run_safety_integration` still reports
`ALL_SAFETY_TESTS_PASSED`).

## Architecture

```
Browser (product/frontend/)
   ↓
FastAPI (product/backend_api/app/)
   ↓
Productization contract (src/smartgrid_mlops/productization/)
   ↓
Existing research implementation (monitoring, governance, agents, audit, evidence, models)
```

The browser does NOT import Python modules and does NOT read research files
directly. Every byte displayed in the UI flows through the Stage 2 API.

## Routes (7)

| Path | View | Spec section |
| --- | --- | --- |
| `/` | Dashboard | § 5, § 6 — executive + the DRIFT → AGENT → GOVERNANCE flow |
| `/forecasts` | Forecasts | § 7 — per-target info, 5-metric, actual vs prediction |
| `/models` / `/models/:model_id` | Models | § 8 — read-only registry, no mutation |
| `/monitoring` | Monitoring | § 9 — events, drift timeline, filters |
| `/governance` | Governance | § 10 — frozen policy, decision log, evaluator |
| `/agents` | Agents | § 11, § 12 — bounded explainer, advisory only |
| `/audit` | Audit | § 13 — evidence-ledger events, honest JSONL wording |

## Components

```
product/frontend/
├── README.md
├── package.json
├── tsconfig.json
├── vite.config.ts
├── vitest.config.ts
├── index.html
└── src/
    ├── main.tsx                  # React entry point (BrowserRouter)
    ├── App.tsx                    # 7-route shell, sidebar, PageErrorBoundary
    ├── styles.css
    ├── api/
    │   ├── client.ts             # typed APIClient; 17 endpoints; no raw fetch() in components
    │   ├── types.ts              # TypeScript types mirroring Pydantic schemas 1:1
    │   └── agentSafety.ts         # isLifecycleCommand + advisoryBlockedNotice
    ├── components/
    │   ├── Sidebar.tsx            # persistent nav + OFFLINE EVALUATION + API status
    │   ├── common.tsx             # StatusPill, SeverityBadge, ErrorBanner, DataTable, Card
    │   └── ErrorBoundary.tsx      # PageErrorBoundary isolates a per-page crash
    ├── hooks/
    │   └── useApi.ts              # useAsync + useApiHealth
    ├── pages/
    │   ├── Dashboard.tsx
    │   ├── Forecasts.tsx
    │   ├── Models.tsx
    │   ├── Monitoring.tsx
    │   ├── Governance.tsx
    │   ├── Agents.tsx
    │   └── Audit.tsx
    └── test/
        ├── setup.ts
        ├── apiClient.test.ts
        ├── apiTypes.test.ts
        ├── agentSafety.test.ts
        └── App.test.tsx
```

## Data sources (read-only)

The frontend consumes the Stage 2 FastAPI service exclusively via
`src/api/client.ts` (one typed class wrapping the 17 endpoints). The 17
endpoints and their backing productization functions are listed in
`docs/productization/api_contract.md` (Stage 2 deliverable).

## Schemas

`src/api/types.ts` mirrors the Stage 2 Pydantic schemas 1:1. No frontend field
is invented; the schema is the contract and the typed client enforces it at
compile time. The build (`tsc -b`) verifies the contract compiles.

## Safety guarantees (Stage 1 + Stage 2 + Stage 3)

| Guarantee | Source of truth | Stage 3 test |
| --- | --- | --- |
| 7/7 lifecycle action types blocked | `tests/test_api_service.py::TestSafetyBoundary` | `App.test.tsx::Sidebar — no mutation UI; quantum claim` |
| OpenAPI schema has no lifecycle path | same | `App.test.tsx::Sidebar — no mutation UI; quantum claim` |
| Stage 1 `run_safety_integration` still passes | `tests/test_productization_safety.py` | implicit (re-runs in CI) |
| Audit uses honest JSONL wording | Stage 2 router | `App.test.tsx::Audit page — JSONL integrity wording is honest` |
| Agent safety UI shows ACTION BLOCKED | `App.test.tsx::Agents page — lifecycle command blocked, advisory request rendered` | same |
| Governance deny is visually distinct | `App.test.tsx::Governance page — deny is visually distinct` | same |
| "OFFLINE EVALUATION" indicator visible | `App.test.tsx::Dashboard — primary workflow story is visible` | same |
| "Quantum/QML: NOT PART OF PROJECT" line | `App.test.tsx::Sidebar — no mutation UI; quantum claim` | same |
| 7 nav links | `App.test.tsx::Sidebar — no mutation UI; quantum claim` | same |

## Test results

- `npx vitest run`: **21 / 21 pass** (4 test files: apiClient, apiTypes, agentSafety, App)
- `npm run build`: **PASS** — 51 modules, 411.86 kB JS / 10.28 kB CSS (gzipped 135.73 kB / 2.53 kB), dist/ generated
- `npx tsc -b`: **PASS** — no TypeScript errors

### Test categories

| Category | Tests | File |
| --- | --- | --- |
| API client behaviour | 4 | `apiClient.test.ts` |
| TypeScript contract mirror | 2 | `apiTypes.test.ts` |
| Agent safety gate (UI) | 6 | `agentSafety.test.ts` |
| App routing, views, target switching, agent safety UI, governance deny, audit wording, error states, sidebar | 9 | `App.test.tsx` |

## Integrity verification (spec section 47)

20 protected Phase 19 artefacts verified byte-identical before and after
the Stage 3 build. All 20 protocol freeze checksums PASS. The Stage 1
safety integration entry point still reports `ALL_SAFETY_TESTS_PASSED`.
The 280 backend tests + 29 API service tests still pass unchanged.

## How to run

```bash
# Backend (in one terminal)
cd /c/Projects/guardrailed-agentic-mlops-smart-grid_trial
.venv/Scripts/python.exe -m uvicorn product.backend_api.app.main:app --port 8000

# Frontend (in another terminal)
cd product/frontend
npm run dev
# open http://127.0.0.1:5173

# Tests
npx vitest run

# Production build
npm run build
```

## Known limitations

| Limitation | Reason |
| --- | --- |
| No live monitoring / streaming | The system is offline evaluation only. Honest labelling. |
| No LLM-backed agent | Local-rule-based; LLM backend interface is a contract only. |
| No quantum / QML / GNN | None in the project. Explicit sidebar line. |
| No authentication | The API is intended for internal use; spec defers auth to a future stage. |
| No Caching, no Redis, no Kafka | Spec section 16 forbids premature infrastructure. |
| No mutation UI | Lifecycle operations remain the responsibility of the existing research pipeline. |

NEXT STAGE: DEMO MODE + DEPLOYMENT/PRESENTATION POLISH
