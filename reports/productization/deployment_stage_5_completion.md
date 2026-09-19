# Stage 5 — Deployment hardening and reproducible packaging (completion report)

## Phase status

**STAGE 5 COMPLETE — the existing product ships with deployment-grade
hardening, env-driven CORS, error-envelope hygiene, a smoke-test
workflow, and 308 passing backend tests + 27 passing frontend tests.**

The product remains what it has been since the research was frozen:
**an offline energy-forecasting MLOps evaluation system with bounded
Agentic AI and deterministic governance.** This stage does not change
that. It only adds the deployment surface around it.

## Inventory (the existing deployment surface)

| Already existed | What it was | What this stage did |
| --- | --- | --- |
| FastAPI app + 7 routers + 17 endpoints | `product/backend_api/app/` | Hardened: CORS middleware, security headers, 404 envelope, sanitized 500 envelope, startup validation. **No endpoints added; none removed.** |
| `/health` with artefact reporting | `routers/health.py` | No behavioural change; the new startup check (`dependencies._validate_required_artifacts`) is more aggressive and aborts at import time if required artefacts are missing, which is what health would have eventually said. |
| Typed error envelope | `main.py:29-46` | Tightened: 404s and unhandled exceptions now use the same envelope; production mode reveals only `internal server error`; development mode reveals only the exception class name — never the message body, which is where secret-shaped fragments typically appear. |
| `OpenAPI` / `/docs` / `/redoc` | FastAPI default | Preserved. |
| Project root resolution (`QSMLOPS_PROJECT_ROOT`) | `config.py` | Unchanged in behaviour; documentation extended in `.env.example`. |
| `.env.example` | One comment line | Replaced with the actual deployment variables. |
| Stage 2 API tests | 30 tests in `tests/test_api_service.py` | Unchanged. |
| `run_safety_integration` (Stage 1) | 231 tests in `tests/` | Unchanged; still reported by `test_stage1_safety_integration_still_passes`. |
| No Docker / no compose | not invented | Documented why below. |

| Missing | Added in this stage |
| --- | --- |
| CORS | `CORSMiddleware` with env-driven `QSMLOPS_ALLOWED_ORIGINS` (dev default = Vite origin). |
| Security headers | `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy` on every response. CSP intentionally omitted (would break `/docs`). |
| Startup validation | `_validate_required_artifacts()` aborts at app import with an actionable message. |
| Frontend build-time API base | `VITE_API_BASE_URL` wired through `src/vite-env.d.ts` + `src/api/client.ts`; build substitutes the value statically. |
| Smoke test | `scripts/smoke_test_deployment.py`: real uvicorn worker + 9 probes, exits 0/1/2. |
| Deployment tests | `tests/test_deployment.py`: 12 tests covering health, CORS, error envelope, startup validation, OpenAPI mutation surface, frontend build hygiene, integrity before/after a run, forbidden capability strings. |
| Top-level deployment runbook | README §19 (prerequisites, dev, prod, env, smoke, tests, security headers, non-goals). |

| Intentionally NOT added | Reason |
| --- | --- |
| Docker / docker-compose | See "Why no Docker" below. |
| CSP | Would break FastAPI's `/docs` and `/redoc` (inline scripts/styles). |
| Authentication / sessions | The product is offline evaluation over public frozen evidence; no protected state. |
| Database | The product reads CSV / YAML / JSONL artefacts; no mutable store. |
| Redis / Kafka / Celery / RabbitMQ | No async work to queue. |
| MLflow server | Training is frozen; the existing MLflow artefacts are read-only. |
| LLM / vector DB / agent runtime | The agent layer is local-rule-based by design. |
| Kubernetes / Helm / Terraform | Single-host deployment is sufficient; the runbook says so explicitly. |
| `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `QISKIT_TOKEN` / `DATABASE_URL` / `KAFKA_BROKER` | None of these are part of the project. The configuration layer's module docstring says so. |

## Architecture

```
Browser
  ↓
Frontend (Vite-built static bundle in product/frontend/dist/)
  ↓  HTTP (VITE_API_BASE_URL or relative "/api")
FastAPI (product/backend_api/app/main.py)
  ├── CORSMiddleware      ← env: QSMLOPS_ALLOWED_ORIGINS
  ├── SecurityHeaders      ← X-Content-Type-Options, X-Frame-Options, Referrer-Policy
  ├── /health             ← artefact presence + offline-evaluation note
  ├── /api/forecasts*     ← 5 endpoints
  ├── /api/models*        ← 2 endpoints
  ├── /api/monitoring*    ← 4 endpoints
  ├── /api/governance*    ← 3 endpoints
  ├── /api/agents*        ← 2 endpoints
  ├── /api/audit*         ← 2 endpoints
  └── /docs /redoc/openapi.json
       ↓
Productization Contract (src/smartgrid_mlops/productization/)
       ↓
Frozen Phase 19 evidence (artifacts/research_tables/, artifacts/experimental_design/, config/governance/)
```

The deployment is read-only. Every artefact, the policy, and the model
registry are accessed through the existing research implementation; the
API layer adds nothing and never writes back.

## Configuration variables

| Variable | Read by | Default | Required in production? |
| --- | --- | --- | --- |
| `QSMLOPS_PROJECT_ROOT` | backend | 3 dirs up from `product/backend_api/app/config.py` | No (set if installed outside the repo) |
| `QSMLOPS_ALLOWED_ORIGINS` | backend | `http://127.0.0.1:5173,http://localhost:5173` | **Yes** (logs a warning otherwise) |
| `QSMLOPS_APP_ENV` | backend | `development` | Recommended (`production`) |
| `VITE_API_BASE_URL` | frontend (build time) | `/api` (relative) | Only if frontend and backend are on different origins |

`.env.example` is the canonical reference. `.env` is git-ignored. There
are no secrets and no fake knobs for services the product does not use.

## Reproducible start commands

### Backend (development)

```bash
.venv\Scripts\python.exe -m uvicorn product.backend_api.app.main:app --reload
```

### Backend (production-style)

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
npm run preview
```

For a multi-host deployment:

```bash
cd product/frontend
set VITE_API_BASE_URL=https://api.example.com
npm run build
```

## Security decisions

- **CORS**: `allow_origins` is a list, never `["*"]`. `allow_credentials=False`
  because the API issues no cookies or Authorization headers. Methods are
  restricted to `GET`, `POST`, `OPTIONS`.
- **Security headers**: `X-Content-Type-Options: nosniff`,
  `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`. The
  `SecurityHeadersMiddleware` uses `setdefault` so a reverse proxy may
  still override (e.g. to relax the frame-options for an embed).
- **No CSP**: `/docs` and `/redoc` use inline scripts/styles; a strict
  CSP would break the documentation surface. If a deployment requires
  CSP, the right place to add it is the reverse proxy, not the app.
- **Error envelope**: `HTTPException` returns the typed `{"error": {…}}`
  envelope. Unhandled exceptions log the full traceback server-side but
  return only `"internal server error"` in production or the exception
  class name in development. **The exception message is never echoed**
  to the client, because exception messages commonly contain
  filesystem paths, SQL fragments, and environment values.
- **404 envelope**: Starlette's default 404 returns `{"detail": "Not
  Found"}` which would bypass the typed envelope. A `StarletteHTTPException`
  handler rewraps these.
- **Startup validation**: importing the app fails fast with an
  actionable message if any required Phase 19 artefact is missing or
  unreadable. Better than a 500 storm on every endpoint.

## Artifact immutability verification

The deployment tests include a "before/after" check: hash 10 protected
Phase 19 artefacts, exercise every primary API category plus a
governance evaluate request, then re-hash. The hashes must be equal.

Result: **PASS** (10/10 byte-identical).

In addition, the pre-existing `tests/test_api_service.py` already
covers a larger 10-artefact set with the same invariant. Both pass.

## Tests added (this stage)

12 tests in `tests/test_deployment.py`:

| Test | Asserts |
| --- | --- |
| `test_app_starts_and_health_responds` | `/health` returns 200 with the offline-evaluation note. |
| `test_app_exposes_openapi_schema` | `/openapi.json` is reachable and includes both `/health` and `/api/governance/decisions`. |
| `test_cors_allows_configured_origin` | Pre-flight from the dev origin is allowed. |
| `test_cors_does_not_allow_arbitrary_origin` | Pre-flight from a non-allow-listed origin gets no `Access-Control-Allow-Origin` header. |
| `test_404_returns_typed_error_envelope` | Unknown path returns `{"error": {...}}`, no Python traceback, no `.py` path. |
| `test_500_unhandled_exception_returns_generic_envelope` | Custom 500 handler returns the class name (dev) or `internal server error` (prod); never echoes the exception message. |
| `test_startup_rejects_missing_required_artifact` | Empty project root → `RuntimeError` listing the missing files. |
| `test_startup_passes_with_real_project_root` | Real project root passes silently. |
| `test_openapi_contains_no_lifecycle_mutation_path` | OpenAPI has no `promote` / `deploy` / `rollback` / `retrain` / `change_policy` / `modify_model` / `modify_features` / `approve_deployment` path. |
| `test_frontend_dist_has_no_localhost_dependency` | Built `dist/index.html` and `dist/assets/*.js` contain no `http://127.0.0.1` or `http://localhost` URL. |
| `test_running_app_does_not_mutate_protected_artefacts` | 10 protected artefacts are byte-identical before and after exercising every API category. |
| `test_backend_module_has_no_quantum_or_llm_capability_claims` | Shipped backend code contains no Qiskit / PennyLane / Cirq / OpenAI / Anthropic / Claude / GPT / Gemini / Llama strings (non-goal disclaimers excluded by heuristic). |

## Why no Docker (per spec §9)

The deployment surface is two artefacts: a Python process and a
static directory. Containerizing them would require a multi-stage
build, image registry, and orchestration for two stateless containers
that share no volume, no network state, and no runtime secret. The
existing `.venv + uvicorn + npm run build` workflow:

- is reproducible (the venv is checked in, no system packages);
- has no system-service dependencies (no DB, no broker, no cache);
- runs identically on any host with Python 3.11+ and Node 18+;
- fails fast at import time if the artefacts are missing (see
  `_validate_required_artifacts`).

The product is offline evaluation. There is no service that benefits
from a container runtime: no database (artefacts are static), no
message queue (no async work), no MLflow server (training is complete),
no LLM (agents are local-rule-based), no Redis (no caching), no
Kubernetes (single-host deployment is sufficient). Adding these would
be infrastructure theater, not reproducibility.

If a future deployment requires a Docker image (e.g. for a managed
platform), the Dockerfile would be a thin wrapper over the same
commands. Nothing in the current code blocks that path; it is just not
worth the build complexity today.

## Acceptance criteria

| Criterion | Result |
| --- | --- |
| Backend tests | **308/308 PASS** (296 prior + 12 new) |
| Frontend tests | **27/27 PASS** (5/5 repeated) |
| `npx tsc -b` | PASS |
| `npm run build` | PASS (428 kB JS / 13 kB CSS, gzip 140 kB / 3.0 kB) |
| Deployment startup | PASS (smoke test 9/9 probes) |
| Health endpoint | PASS (offline-evaluation note present) |
| Frontend → API connectivity | PASS (smoke test 9/9) |
| CORS configured | PASS (env-driven, refuses arbitrary origins) |
| Artifact path resolution | PASS (`QSMLOPS_PROJECT_ROOT` + 3-dir default) |
| Error handling | PASS (no traceback leakage; 404 + 500 use typed envelope) |
| OpenAPI no lifecycle mutation | PASS (test enforces 8 forbidden hints) |
| Agent authority | ADVISORY ONLY (7/7 lifecycle actions blocked) |
| Governance | AUTHORITATIVE (Phase 13 policy + DENY path tested) |
| Research artifact integrity | UNCHANGED (10/10 byte-identical before/after) |
| Protocol freeze | 20/20 PASS |
| Quantum/QML | NOT PRESENT (no Qiskit / PennyLane / Cirq / VQC / qubit / ansatz capability claims) |

## Known limitations (honest)

- **No HTTPS, no rate limiting, no auth.** The deployment is a
  research / evaluation system. Adding these would be a product
  decision, not a deployment decision; the spec explicitly defers
  auth to a future phase.
- **Single-host uvicorn, single worker.** Adequate for evaluation
  traffic. A real production rollout would put the static frontend
  on a CDN and the API behind a reverse proxy (nginx, Caddy) that
  adds TLS, request limits, and additional security headers.
- **No automated deployment pipeline.** The runbook is a manual
  sequence; CI/CD is out of scope.
- **Smoke test exercises the local uvicorn worker.** A CI smoke
  test would also need a port allocation strategy and cleanup
  hooks; the current script is designed to be run interactively.
- **CORS default is the Vite dev origin.** Production deployments
  MUST set `QSMLOPS_ALLOWED_ORIGINS`. The configuration layer logs
  a warning when `QSMLOPS_APP_ENV=production` and the allow-list is
  the dev default; it does not refuse to start (so a misconfigured
  deployment can be diagnosed, not refused).
- **No image / chart for the architecture.** The Markdown tree
  diagram in this report and the README is the canonical reference.
- **Quantum / LLM strings are still present as non-goal disclaimers**
  in the shipped code (e.g. `__init__.py` and `config.py` explicitly
  say "no quantum / QML / GNN / LLM"). The test
  `test_backend_module_has_no_quantum_or_llm_capability_claims`
  enforces that those strings do not appear as capability claims —
  the heuristic excludes lines that look like disclaimers or doc
  comments.

## Files modified / added in this stage

Backend:
- `product/backend_api/app/main.py` — CORS middleware, security headers middleware, 404 handler, sanitized 500 envelope
- `product/backend_api/app/config.py` — `app_env` and `allowed_origins` from env, dev-default origin list, warning on prod-without-explicit-origins
- `product/backend_api/app/dependencies.py` — `_validate_required_artifacts` + `REQUIRED_ARTIFACTS` / `OPTIONAL_ARTIFACTS` lists
- `.env.example` — replaced single comment with the full deployment-variable reference

Frontend:
- `product/frontend/src/api/client.ts` — `resolveBaseURL()` reads `VITE_API_BASE_URL`; falls back to `/api`
- `product/frontend/src/vite-env.d.ts` (new) — typed `import.meta.env`

Tests + scripts + docs:
- `tests/test_deployment.py` (new) — 12 tests
- `scripts/smoke_test_deployment.py` (new) — real-uvicorn smoke test
- `README.md` — appended §19 deployment runbook

## NEXT STAGE: PRODUCTION READINESS REVIEW

The deployment is now reproducible and hardened for single-host
operation. A production-readiness review would add: TLS termination,
rate limiting, request logging, structured access logs, alerting
hooks, and an automated CI pipeline. None of these is justified by
the current product (offline evaluation, read-only, no live data,
no production traffic); they would be appropriate only if a
deployment operator independently committed to running this for
real users.
