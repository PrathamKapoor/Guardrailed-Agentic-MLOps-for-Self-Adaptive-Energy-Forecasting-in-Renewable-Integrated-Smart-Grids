# Final Release Manifest — Guardrailed Agentic MLOps (Smart-Grid Forecasting)

This document records the final release state of the repository. It is a
closure artifact, not a development artifact. It freezes the declared
product scope, the verified baseline, the authority model, the known
limitations, the low-severity disclosures, and the final verdict.

---

## 1. Product identity

**Name:** Guardrailed Agentic MLOps for Self-Adaptive Energy Forecasting
in Renewable-Integrated Smart Grids

**Repositories / surfaces:**

- `src/smartgrid_mlops/` — the 20-phase research package (frozen).
- `product/backend_api/` — the thin FastAPI product layer (17 endpoints).
- `product/frontend/` — the React + Vite dashboard (9 routes incl. Demo).
- `dashboard/` — the static evidence dashboard (`index.html`,
  `charts.html`, pre-built JSON snapshots).
- `hackathon/` — the judge-facing landing page.
- `docs/`, `reports/`, `artifacts/`, `config/`, `data/` — research
  evidence and frozen artefacts.

## 2. Declared scope

> This repository provides a reproducible offline evaluation and
> demonstration platform for energy forecasting MLOps. It productizes
> frozen forecasting research artifacts through monitoring, bounded
> advisory agents, deterministic governance, audit evidence, a FastAPI
> API, and a React dashboard. Agents may analyze and explain evidence
> but cannot execute lifecycle actions; governance remains
> authoritative.

The single supported deployment claim is:

> A reproducible, deployable, single-machine offline evaluation and
> demonstration platform.

## 3. Explicit non-goals

The product is NOT, and does not claim to be:

- a live smart-grid control system;
- a real-time forecasting service;
- a streaming telemetry platform;
- an autonomous remediation system;
- a cloud-scale production system;
- a multi-user SaaS;
- an LLM-backed reasoning system;
- a Quantum/QML/GNN system.

No documentation, dashboard, API endpoint, or CLI entry point may be
read to imply otherwise. The active surfaces (README §1–§19,
`hackathon/index.html`, `dashboard/`, `product/**/README.md`,
`docs/productization/`, the 20 phase reports) tell one consistent
story: offline evaluation, read-only, advisory agents, authoritative
governance.

## 4. Architecture summary

```
Browser
  ├─ / (Dashboard)   ── product/frontend (React + Vite, built to dist/)
  ├─ /demo           ── primary (7 steps) + safety (5 steps) + presentation mode
  └─ /forecasts | /models | /monitoring | /governance | /agents | /audit
        │
        ▼  (VITE_API_BASE_URL or relative "/api")
FastAPI  (product/backend_api/app/main.py)
  ├─ CORSMiddleware        ← QSMLOPS_ALLOWED_ORIGINS
  ├─ SecurityHeaders        ← nosniff / X-Frame-Options / Referrer-Policy
  ├─ /health               ← offline-evaluation health (artefact presence)
  ├─ /api/forecasts*        ← 5 endpoints
  ├─ /api/models*           ← 2 endpoints
  ├─ /api/monitoring*       ← 4 endpoints
  ├─ /api/governance*       ← 3 endpoints
  ├─ /api/agents*          ← 2 endpoints
  ├─ /api/audit*            ← 2 endpoints
  └─ /docs /redoc /openapi.json
        │
        ▼
Productization contract (src/smartgrid_mlops/productization/)
        ▼
Frozen Phase 0..19 evidence (artifacts/, config/, data/)
```

The API contains no lifecycle-mutation endpoint. The frontend sends
only `GET` and a bounded set of advisory `POST`s. The product layer
adds no business logic; it is a thin wrapper over the frozen research
implementation.

## 5. Authority model

```
AGENT
  ├─ analyzes
  ├─ retrieves evidence
  ├─ explains
  ├─ recommends (advisory only)
  └─ CANNOT mutate lifecycle state

GOVERNANCE
  ├─ evaluates evidence
  ├─ applies frozen policy (Phase 13, v13.0.0)
  ├─ ALLOW / DENY / REQUIRE_APPROVAL decisions
  └─ is authoritative

PRODUCT / API
  ├─ exposes read/advisory surfaces
  └─ exposes NO lifecycle mutation endpoint
```

### The seven blocked lifecycle actions (verified 7/7)

```
PROMOTE
DEPLOY
ROLLBACK
RETRAIN
CHANGE_POLICY
MODIFY_MODEL
MODIFY_FEATURES
```

Each is intercepted by `smartgrid_mlops.agents.firewall.firewall_validate`
(allow-list only: INVESTIGATE / SUMMARIZE / EXPLAIN /
REQUEST_HUMAN_REVIEW / CREATE_REPORT) and, at the API boundary, confirmed
absent from the OpenAPI schema
(`tests/test_deployment.py::test_openapi_contains_no_lifecycle_mutation_path`)
and from the product source tree (manual grep of
`product/backend_api/app/` finds no mutation code path).

## 6. Canonical verification commands

All commands below were executed and verified **during this release
closure** (results in §7). Do not document or rely on commands that were
not actually run.

### Backend verification

```bash
.venv\Scripts\python.exe -m pytest
```

### Backend API (development)

```bash
.venv\Scripts\python.exe -m uvicorn product.backend_api.app.main:app --reload
```

### Backend API (production-style, single worker)

```bash
.venv\Scripts\python.exe -m uvicorn product.backend_api.app.main:app --host 0.0.0.0 --port 8000 --workers 1
```

### Frontend (development)

```bash
cd product/frontend
npm install
npm run dev
```

### Frontend (production build)

```bash
cd product/frontend
npm run build
# preview the built bundle
npm run preview
```

### Frontend → backend base URL (multi-origin deployments only)

```bash
cd product/frontend
set VITE_API_BASE_URL=https://api.example.com
npm run build
```

### TypeScript check

```bash
cd product/frontend
npx tsc -b
```

### Deployment smoke test (real Uvicorn worker)

```bash
.venv\Scripts\python.exe scripts/smoke_test_deployment.py --port 8765
```

## 7. Final test/build results (re-verified this closure)

| Check | Command | Result |
| --- | --- | --- |
| Backend test suite | `.venv\Scripts\python.exe -m pytest` | **308 passed, 0 failed, 1 warning** (3:41) |
| Frontend test suite | `npm test` (`vitest run`) | **27 passed, 0 failed** (5/5 repeated) |
| TypeScript | `npx tsc -b` | **PASS** (exit 0) |
| Production build | `npm run build` | **PASS** (428.56 kB JS / 13.41 kB CSS, gzip 139.75 kB / 2.97 kB) |
| Deployment smoke test | `scripts/smoke_test_deployment.py` | **9/9 probes passed** |
| Protocol freeze | SHA-256 sidecar scan | **20/20 PASS** (3 multi-line dataset manifests skipped — pre-existing) |
| Protected Phase 19 artefacts | `phase19_integrity_baseline.json` | **20/20 byte-identical, 0 changed, 0 missing** |

> **Chronology note:** Stages 7–14 were completed after this v1 release
> closure. The current post-Stage-14 baseline is **481 backend tests passed,
> 27 frontend tests passed**, with all protocol-freeze and Phase 19
> integrity checks unchanged. See `stage_14_governance_re_evaluation_completion.md`
> for the most recent verified counts. The v1 figures above are preserved
> as the correct snapshot at the time of the original v1 release closure.

## 8. Artifact integrity status

`artifacts/ui_build/phase19_integrity_baseline.json` records 20
protected Phase 19 artefacts (plus 2 metadata keys) with SHA-256 and
size. Re-verified this closure: **20/20 byte-identical**. No
implementation change was made during this closure, and the audit itself
mutated nothing.

## 9. Protocol freeze status

20 protocol-freeze `.sha256` sidecars across `artifacts/` are valid.
Three `.sha256` files are multi-line dataset manifests
(`opsd_time_series_checksums.sha256`, `rts_gmlc_checksums.sha256`, and
the HPO best-configs `checksums.sha256`) and are skipped by the scanner
as they reference external downloads; they are unchanged and not
failures.

## 10. Deployment status

| Class | Status |
| --- | --- |
| Single-machine, single-tenant, offline | **READY** — `venv + uvicorn + npm run build`; smoke test 9/9 |
| Internet-exposed | **NOT READY** — no TLS termination, rate limiting, or auth in the app |
| Multi-user / multi-tenant | **OUT OF SCOPE** — no user model; auth is a product-scope change |

The deployment runbook is `README.md` §19 and
`product/backend_api/README.md`. No Docker, no compose, no Kubernetes,
no cloud provider is introduced (the product has no service that
justifies them).

## 11. Known limitations

Current-product limitations (NOT blockers for the declared scope):

- Single-machine.
- Single-tenant.
- Offline evaluation (no live data, no streaming, no telemetry).
- No authentication.
- No TLS termination.
- No rate limiting.
- No per-request access logging.
- No model serving / real-time inference.
- No LLM-backed agents (local-rule-based backend only).
- No live drift detection (drift events are one-shot derived from the
  frozen final-test evidence).
- Governance decisions require the frozen policy; there is no
  operational deployment/canary path.

## 12. Low-severity disclosures

Preserved from Stage 6; none implemented during this closure.

1. **Agent endpoint append-only writes** — `POST /api/agents/explain`
   appends to `artifacts/mlops/audit/events.jsonl` and
   `artifacts/agents/phase_18/memory/agent_memory.jsonl`. This is
   evidence/memory bookkeeping required by the research contract, NOT
   lifecycle mutation. No test currently asserts these are the *only*
   permitted write targets.
2. **Stale paper draft** — `docs/paper/results.md` (and its sibling
   `.md` files in `docs/paper/`) describe a historical Phase 0 run with
   synthetic data and dummy models (MAE ~49.5). It is NOT linked from
   any active surface (`README`, `hackathon/index.html`, `dashboard/`).
   The active `docs/paper_drafts/` set is the current, honest draft set.
3. **Heavy research dependencies** — `pyproject.toml` declares
   `pyarrow`, `scikit-learn`, `torch`, `optuna`, `mlflow`; the product
   API uses none of them at runtime. `pip install -e .` installs ~5 GB
   of unnecessary ML libraries. The correct product install command is
   `.venv\Scripts\python.exe -m pip install fastapi uvicorn httpx`.

## 13. Future live-system requirements

Required only for a future live operational smart-grid system — NOT in
the current declared scope and NOT defects of the current product:

- Real-time telemetry ingestion and streaming architecture.
- Authentication and authorization (RBAC/ABAC).
- Persistent operational database (e.g. PostgreSQL/TimescaleDB).
- Model serving and live inference.
- Live drift detection (online algorithms).
- Operational monitoring, alerting, and incident response.
- Model retraining infrastructure and deployment orchestration.
- Rollback infrastructure (traffic shifting, model registry).
- Secrets management and cloud/network hardening.
- High availability (multi-region, load balancing).
- Rate limiting and multi-user access control.
- Compliance (SOC 2, ISO 27001, IEC 62443 / NERC CIP for energy).

None of these is implemented here, and none is required for the
declared offline evaluation and demonstration platform.

## 14. Final release verdict

```
FINAL RELEASE VERDICT

READY FOR DECLARED OFFLINE PRODUCT SCOPE
```

Separately and unambiguously:

```
LIVE OPERATIONAL SMART-GRID SYSTEM

NOT IN CURRENT PRODUCT SCOPE
NOT READY
REQUIRES A SEPARATE ARCHITECTURE, SECURITY MODEL,
OPERATIONAL MODEL, AND REGULATORY REVIEW
```

---

## Research-integrity classification of documentation

| Path | Classification | Basis |
| --- | --- | --- |
| `README.md` | ACTIVE | Consistently offline/read-only/advisory/authoritative; §19 runbook verified |
| `hackathon/index.html` | ACTIVE | Judge-facing; real Phase 19 numbers; no quantum/LLM capability claim |
| `dashboard/` | ACTIVE | Real Phase 19 evidence; read-only static UI |
| `product/backend_api/README.md` | ACTIVE | Consistent with top-level README |
| `product/frontend/README.md` | ACTIVE | Consistent |
| `docs/productization/*` | ACTIVE | API contract + integration doc; honest |
| `docs/paper_drafts/` (12 files) | ACTIVE | Real Phase 19 results; synthetic scenarios labelled as simulation |
| `docs/research_methodology/*` | ACTIVE | Honest limitation language |
| `reports/phase_00..20_completion.md` | HISTORICAL (frozen) | Phase reports; Phase 19 is authoritative |
| `reports/productization/*` | ACTIVE | Stage 2–6 completion + readiness review |
| `docs/paper/` (11 files incl. `results.md`) | **STALE / QUARANTINED** | Phase 0 synthetic placeholder; NOT linked from active surfaces |
| `docs/hackathon_*.md`, `docs/HACKATHON_READY.md` | ACTIVE | Consistent |

The one stale directory (`docs/paper/`) is explicitly classified
STALE/QUARANTINED and is not deleted (scientific history is preserved
verbatim). It is not referenced by any release, runbook, or product
surface, so it cannot be mistaken for the released product's results.

---

**BASELINE FROZEN.** No further development stage is defined.