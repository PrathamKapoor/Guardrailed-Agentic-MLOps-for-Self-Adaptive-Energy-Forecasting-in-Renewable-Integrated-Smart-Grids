# Guardrailed Agentic MLOps — Frontend Dashboard (Stage 3)

This is the **frontend operations console** for the Guardrailed Agentic MLOps
platform. It consumes the Stage 2 FastAPI service exclusively; it does not
read research artefacts directly, does not duplicate the existing MLOps logic,
and does not expose any lifecycle mutation UI.

The existing `dashboard/` directory (Phase 20 static research evidence
interface) remains the read-only research evidence surface. This frontend
is the operational console built on top of the Stage 2 API.

## Architecture

```
Browser (this package: product/frontend/)
   ↓
FastAPI (Stage 2: product/backend_api/)
   ↓
Productization Contract (src/smartgrid_mlops/productization/)
   ↓
Existing research implementation
   (monitoring, governance, agents, evidence ledger, frozen Phase 19 artefacts)
```

The browser does not import Python modules and does not read research files
directly. The API is the contract.

## Tech

- **React 18** + **TypeScript 5** + **Vite 5**
- **react-router-dom 6** for the 7 routes + 1 detail route
- **Chart.js 4** (only registered for chart module; current views use canvas)
- **Vitest 2** + **@testing-library/react 16** for tests (jsdom)
- No backend duplication, no third-party CDN, no fake realtime infra.

## Routes

| Path | View | Purpose |
| --- | --- | --- |
| `/` | Dashboard | Executive overview + the primary DRIFT → AGENT → GOVERNANCE flow |
| `/forecasts` | Forecasts | Per-target metrics, 5-metric result, actual vs prediction canvas |
| `/models` / `/models/:model_id` | Models | Existing research registry, read-only |
| `/monitoring` | Monitoring | Drift + performance + health events with filters |
| `/governance` | Governance | Frozen policy, decision log, governance evaluator |
| `/agents` | Agents | Bounded agent explanation (advisory only); lifecycle actions blocked |
| `/audit` | Audit | Existing evidence-ledger events + honest JSONL verification |

## Files

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
    ├── styles.css                 # dark research theme
    ├── api/
    │   ├── client.ts             # typed APIClient over the 17 FastAPI endpoints
    │   ├── types.ts              # TypeScript types mirroring the Pydantic schemas 1:1
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

## Safety guarantees preserved at the UI layer

- **No mutation UI**: no Promote, Deploy, Rollback, Retrain, ChangePolicy,
  ModifyModel, ModifyFeatures buttons. Verified by
  `App.test.tsx::Sidebar — no mutation UI; quantum claim` and by the absence
  of those verbs in any rendered text (no exception is raised if a user
  types one, but the agent endpoint refuses to execute it and renders the
  "ACTION BLOCKED" notice).
- **Honest wording on audit**: `/api/audit/verify` returns "VALID JSONL" — the
  UI labels this exactly. It does not claim "cryptographically verified"
  because no hash chain exists in the current implementation.
- **"OFFLINE EVALUATION" indicator** is visible in the sidebar at all times.
- **"Quantum/QML: NOT PART OF PROJECT"** line is rendered in the sidebar
  footer.
- **Stage 1 safety integration** is preserved end-to-end: re-running
  `run_safety_integration` from the productization layer still reports
  `ALL_SAFETY_TESTS_PASSED`. The API service test suite (29 tests) is unchanged.
- **Phase 19 integrity** is preserved: the 20 critical artefacts recorded in
  `artifacts/ui_build/phase19_integrity_baseline.json` are byte-identical
  before and after the frontend was built.

## How to run

### Install

```bash
cd product/frontend
npm install
```

### Dev (with the API running on http://127.0.0.1:8000)

```bash
# in another terminal, start the backend:
cd /c/Projects/guardrailed-agentic-mlops-smart-grid_trial
.venv/Scripts/python.exe -m uvicorn product.backend_api.app.main:app --port 8000

# in product/frontend:
npm run dev
# open http://127.0.0.1:5173
```

Vite proxies `/api` and `/health` to `http://127.0.0.1:8000` (see `vite.config.ts`).

### Production build

```bash
npm run build
```

Result: a static `dist/` directory (`index.html` + 1 JS bundle + 1 CSS file).

### Tests

```bash
npm test
```

Result: 21/21 pass.

### Typecheck

```bash
npx tsc -b --noEmit
```

## Honest limitations

- The system is **offline evaluation only**. The dashboard is honest about
  this: the sidebar carries an "OFFLINE EVALUATION" pill and the page lede
  paragraphs say so.
- The productization layer's monitoring events are derived from a one-shot
  read of the frozen final-test evidence. There is no streaming, no live
  telemetry, no real-time inference.
- The agent layer is local-rule-based; the bounded-agent endpoint is
  advisory only. Lifecycle action types are blocked by the firewall at
  the audit-module level; the UI does not pretend otherwise.
- No LLM is invoked at runtime. The LLM backend interface is documented as a
  contract only.
- No quantum / QML / GNN is introduced anywhere.
- No authentication is added; the API is intended for internal use.

## Acceptance criteria (per spec section 24)

- [x] dashboard runs locally
- [x] all primary routes work
- [x] API integration works (every view consumes the Stage 2 API)
- [x] forecasting charts use real API data
- [x] registry uses real API data
- [x] monitoring uses real API data
- [x] governance uses real API data
- [x] agent explanation uses the bounded agent API
- [x] audit uses the real audit API
- [x] no direct filesystem access exists in frontend
- [x] no lifecycle mutation buttons bypass governance
- [x] offline limitations are accurately represented
- [x] responsive layout works
- [x] frontend tests pass (21/21)
- [x] backend/research tests remain unchanged and passing (280/280)
- [x] protected research artefact hashes remain unchanged
- [x] production build passes
