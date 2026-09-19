# Guardrailed Agentic MLOps for Self-Adaptive Energy Forecasting in Renewable-Integrated Smart Grids

> A 20-phase, governance-first MLOps system for electricity forecasting with a bounded, firewalled agentic decision-support layer and a frozen, fully audited final evaluation.

## Quick start

```bash
# 1. Canonical Paper Reproduction (validates all research tables, figures, and protocols)
python reproduce_paper.py --quick    # Rapid verification (~15s)
python reproduce_paper.py --full     # Full experiment execution across all phases

# 2. Evidence API (read-only; requires the repo virtualenv)
.venv/Scripts/python -m uvicorn product.backend_api.app.main:app --port 8000
# 3. Frontend console
cd product/frontend && npm install && npm run dev   # http://localhost:5173
# 4. Verify the sealed final-evaluation artifacts (read-only check)
.venv/Scripts/python run_final_evaluation.py
```

## 1. Demo

**Open `hackathon/index.html` first** — it is the judge-facing entry point. It links into the primary interactive evidence interface at **`dashboard/index.html`**.

| Surface | Path | What it shows |
| --- | --- | --- |
| Hackathon landing | `hackathon/index.html` | Hero, problem, solution, architecture, results, uniqueness, demo, quick start, evidence, reproducibility, limitations |
| Evidence dashboard | `dashboard/index.html` | Executive overview, per-target cards, benchmark table, error analysis, model/feature/protocol/lineage/governance/audit/artifacts panels |
| Interactive chart | `dashboard/charts.html` | Canvas-based actual-vs-predicted with date-range filter |

The 90-second demo script (`docs/hackathon_demo_script.md`) and the 3-minute demo script (`docs/hackathon_demo_3min.md`) describe exactly what to click.

## 2. Headline result (locked test partition 2020-11-01 → 2020-12-31, 1464 hourly rows per target)

| Target | Frozen model MAE | External benchmark MAE | Δ relative | Result |
| --- | --- | --- | --- | --- |
| PV (random_forest, B_lags_only) | 36.12 | 39.09 (H24 daily persistence) | **−7.61%** | **Better** |
| LOAD (random_forest, B_lags_only) | 174.26 | 101.14 (RTS_DAY_AHEAD) | +72.29% | Worse |
| WIND (hist_gradient_boosting, B_lags_only) | 778.84 | 331.30 (RTS_DAY_AHEAD) | +135.08% | Worse |

Lower MAE is better. The PV result is the only benchmark comparison the frozen models win. LOAD and WIND do not beat the published RTS_DAY_AHEAD forecast on this 2-month window. The system reports both outcomes transparently. The result is reproducible from `artifacts/research_tables/final_model_comparison.csv`.

## 3. Problem

Operating an MLOps forecasting system for energy is hard because the system that monitors the model, the system that retrains it, and the system that promotes it all want to make the same kinds of decisions: change the model, change the policy, change the data, change the threshold. When an autonomous agent is added to that mix, it tends to drift toward the highest-leverage action: change the policy, promote the model, retrain. That is also the most dangerous action in a safety-critical setting.

Most "agentic MLOps" projects solve this by making the agent the operator: it makes the calls, the dashboard reports. We asked the opposite question: *can a bounded, firewalled agent reduce explanation burden without controlling the lifecycle?*

## 4. Solution

A 20-phase pipeline that ends in a frozen, fully audited evaluation on the locked test partition. Five specialised agents sit beside the lifecycle and can only explain, retrieve, and report — they cannot promote, retrain, or change features.

1. **Tracking & governance** — every model, run, and decision is captured with cryptographic identity.
2. **Drift monitoring** — PSI / KS feature drift, prediction drift, and rolling performance drift over 168-hour windows.
3. **Governed retraining** — retraining requests pass a 17-gate policy; final results are 18 REGISTERED_CHALLENGER entries, all blocked from promotion by the benchmark gate.
4. **Champion–challenger + rollback** — promotion requires 13 governance gates plus a passing canary; rollback is verified, not just attempted.
5. **Bounded agentic decision support** — a firewall allows only `INVESTIGATE / SUMMARIZE / EXPLAIN / REQUEST_HUMAN_REVIEW / CREATE_REPORT`; lifecycle actions are blocked and audited.
6. **FROZEN final evaluation** — the 18 registered challengers are evaluated on the locked test partition with the frozen reference and a published external benchmark.

## 5. Architecture

Two diagrams in `hackathon/architecture.svg` (system) and `hackathon/progression.svg` (research progression) are readable in any browser and reflect the actual 20-phase implementation. No conceptual boxes that do not exist in code.

## 6. Key innovation

A governance firewall that keeps agentic AI from controlling the lifecycle. Allowed: `INVESTIGATE / SUMMARIZE / EXPLAIN / REQUEST_HUMAN_REVIEW / CREATE_REPORT`. Blocked: `PROMOTE_MODEL / ROLLBACK_MODEL / CHANGE_POLICY / START_RETRAINING / CHANGE_FEATURES` plus anything unknown (deny-by-default). The forbidden audit events `AGENT_MODEL_PROMOTED` and `AGENT_RETRAINING_STARTED` cannot be emitted by construction. The Phase 18 ablation measured **0 lifecycle differences** and **14 of 14 unsafe recommendations blocked**.

## 7. Results (full table)

See `artifacts/research_tables/final_forecasting_results.csv` and `final_model_comparison.csv` for the complete per-target, per-configuration MAE / RMSE / sMAPE / nMAE / nRMSE. The dashboard's "Benchmark comparison" section presents them inline.

**Post-v1 research highlight (Stage 10):** residual forecast correction research achieved MAE 1.54 for the best LOAD candidate — approximately a 98.5% reduction versus the referenced day-ahead baseline. **This is research evidence, not a promoted model.** The existing frozen GovernanceEngine later evaluated all seven candidates and returned DENY for each (Stages 12 and 14), confirming that a strong research metric does not bypass deterministic governance.

## 7a. Post-v1 research and evaluation extensions (Stages 7–14)

After the original v1 productization release, eight additional research and governance stages were completed. All outputs are isolated under `artifacts/v2/`. None promotes a model, deploys a model, or mutates any lifecycle state.

| Stage | Capability | Output namespace | Key result |
| --- | --- | --- | --- |
| 7 | Historical Telemetry Replay | `artifacts/v2/telemetry_replay/` | Historical/simulated replay only; NOT live telemetry. |
| 8 | Incremental Monitoring | `artifacts/v2/incremental_monitoring/` | Rolling monitoring over replayed data with warm-up and chronological guarantees. |
| 9 | Forecasting Research | `artifacts/v2/forecasting_research/` | Honest baseline comparison; PV remained the strongest frozen finalist while LOAD/WIND weaknesses were exposed. |
| 10 | Residual Forecast Correction | `artifacts/v2/residual_forecasting/` | Strong research improvements; best LOAD candidate achieved MAE 1.54 (−98.5% vs baseline). Research evidence only. |
| 11 | Research Validation | `artifacts/v2/research_validation/` | Chronological folds, leakage detection (0 violations in 97,747 checks), feature ablation, robustness classification. |
| 12 | Governance Evaluation | `artifacts/v2/governance_evaluation/` | 7/7 candidates DENYed by the existing frozen GovernanceEngine due to formal evidence gaps. |
| 13 | Candidate Packaging | `artifacts/v2/governance_candidate_packages/` | Formal evidence packages prepared without promotion or lifecycle mutation. |
| 14 | Governance Re-Evaluation | `artifacts/v2/governance_re_evaluation/` | The authoritative GovernanceEngine again evaluated all seven candidates and DENYed them. |

**GOOD RESEARCH METRICS ≠ AUTOMATIC LIFECYCLE APPROVAL.** The governance engine remains authoritative.

## 8. Honest limitations

- One year (2020, leap year) of one dataset (RTS-GMLC). 8,784 hourly rows. Final test is November–December 2020 only.
- Classical ML only: random forest, hist gradient boosting, MLP. No deep learning, no quantum, no GNN, no LLM (the LLM backend interface is documented as a contract only).
- External benchmark (RTS_DAY_AHEAD) is a published operating artefact; beating it on LOAD/WIND is genuinely hard for short-horizon ML models.
- The agent operational benefit (~72% time reduction in explanation effort) is measured by a scenario-based analytical workload model, not by an empirical human-subject user study.
- The system is offline evaluation only. There is no production deployment, no live serving, no streaming ingestion.

## 9. Installation

Requires Python 3.11+ on Windows / macOS / Linux. No GPU. No network. ~3 minutes.

```bash
git clone <repo-url>
cd guardrailed-agentic-mlops-smart-grid
python -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

Detailed installation: `docs/hackathon_installation.md`.

## 10. Quick start

```bash
# Run the test suite (513 backend tests; 27 frontend tests)
.venv\Scripts\python.exe -m pytest

# Run canonical paper reproduction
python reproduce_paper.py --quick    # Artifact & protocol verification (<20s)
python reproduce_paper.py --full     # Full experiment execution (~10m)

# Open the primary demo
start dashboard/index.html
```

For a judge, that's three commands and a single browser open.

## 11. Demo commands

- `python scripts/bootstrap_rts_gmlc.py --verify-only` — RTS data integrity check (expected: PASS).
- `python scripts/build_dashboard.py` — re-emit the dashboard data snapshots from Phase 19 artefacts (read-only with respect to them).
- `python -m pytest tests/test_phase20_dashboard.py` — run only the dashboard tests (18 tests).
- `python -m pytest tests/test_adversarial_firewall.py` — run adversarial firewall tests (31 tests).

## 12. Repository structure

```
AGENTS.md                                    # governance + workflow rules
README.md                                    # this file
reproduce_paper.py                           # canonical one-command paper reproduction
CITATION.cff                                 # citation metadata
CONTRIBUTING.md                              # contributor guidelines
pyproject.toml                               # build + dependencies
docs/                                        # research documentation
  PAPER_CODE_MAP.md                          # paper claims to code and artifact traceability map
  paper/                                     # paper results and limitations documentation
  research_methodology/                      # 24+ methodology documents
  paper_drafts/                              # 12 paper-draft documents
  architecture_overview.md
  hackathon_*.md                             # hackathon layer docs
  HACKATHON_READY.md                         # hackathon submission checklist
artifacts/
  experimental_design/                       # 20 protocol freeze files + SHA-256s
  model_registry/                            # forecasting reference + lifecycle + challengers
  experiments/final_evaluation/phase_19/     # frozen final evaluation evidence
  paper_evidence/                            # evidence registry (154 entries)
  research_tables/                           # spec-named CSVs (multi-horizon, drift, governance, etc.)
  research_figures/                          # Phase 19 + comprehensive research figures (PNG + SVG)
  audit/                                     # final execution audit JSON
  mlops/lineage/                             # final evaluation lineage report
  ui_build/                                  # Phase 19 integrity baseline (20 SHA-256s)
  v2/                                        # post-v1 stage outputs (Stages 7–14)
data/processed/                              # canonical research_hourly_index.parquet + per-target parquets
dashboard/                                   # Phase 20 read-only evidence interface
  index.html, charts.html, styles.css, app.js
  data/                                      # pre-built JSON snapshots
hackathon/                                   # hackathon-facing landing + SVGs
reports/                                     # 20 phase completion reports + completion.md
scripts/                                     # 30+ scripts (pipeline + finalize + audit + research experiments)
src/smartgrid_mlops/                         # Python package
tests/                                       # 513 backend tests + 27 frontend tests
```

## 13. Reproducibility

- All currently defined automated tests pass (513 backend tests, 0 fail; 27 frontend tests, 0 fail). `pytest` is the canonical test command.
- `python reproduce_paper.py --quick` performs rapid artifact and protocol verification (<20s).
- `python reproduce_paper.py --full` executes the complete experiment suite from raw data (~10 min on CPU).
- 20 protocol freezes are SHA-256-validated. See `docs/hackathon_installation.md` step 8.
- 20 critical Phase 19 artefacts are recorded in `artifacts/ui_build/phase19_integrity_baseline.json` and verified byte-identical at the end of the hackathon build.
- The 18 dashboard tests include a regression test that re-runs the dashboard builder and confirms no Phase 19 artefact changes.

## 14. Research documentation

- 20 phase completion reports under `reports/phase_00..20_completion.md`.
- 20 frozen protocol artefacts under `artifacts/experimental_design/`.
- 12 paper drafts under `docs/paper_drafts/`.
- 24+ research methodology documents under `docs/research_methodology/`.
- The full MLflow lineage under `artifacts/mlflow/`.
- The evidence registry under `artifacts/paper_evidence/evidence_registry.yaml` (154 entries).
- The 4 Phase 19 figures (performance, error distribution, forecast vs actual, system architecture) under `artifacts/research_figures/phase_19/`.
- Detailed verification and completion reports for the post-v1 research and governance stages are available in `reports/productization/`:
  `stage_7_telemetry_replay_completion.md`,
  `stage_8_incremental_monitoring_completion.md`,
  `stage_9_completion.md`,
  `stage_10_completion.md`,
  `stage_11_completion.md`,
  `stage_12_governance_evaluation_completion.md`,
  `stage_13_candidate_packaging_completion.md`,
  `stage_14_governance_re_evaluation_completion.md`,
  `final_release_manifest.md`,
  `final_submission_readiness_audit.md`.

## 15. Citation

The frozen final evaluation is described in `reports/phase_19_completion.md`. The bounded agentic decision-support layer is described in `docs/research_methodology/bounded_agentic_ai.md` and `reports/phase_17_completion.md`. The champion-challenger + rollback layer is described in `reports/phase_16_completion.md`. The drift monitoring and governed retraining layers are described in `reports/phase_14_completion.md` and `reports/phase_15_completion.md`.

## 16. Team / contributors

The repository was produced by a single research agent. See `handoff.md` for the full project history (one comprehensive inspection of the repository, no external collaborators).

## 17. Hackathon submission

- Hackathon landing page: `hackathon/index.html`
- 90-second demo script: `docs/hackathon_demo_script.md`
- 3-minute demo script: `docs/hackathon_demo_3min.md`
- Recording script: `docs/hackathon_recording_script.md`
- Judge FAQ: `docs/hackathon_faq.md`
- Judging matrix: `docs/hackathon_judging_matrix.md`
- USP (3 versions) and tagline: `docs/hackathon_usp.md`
- Installation: `docs/hackathon_installation.md`
- Submission checklist: `docs/HACKATHON_READY.md`
- Final report: `reports/hackathon_readiness_completion.md`

## 18. License

Proprietary / research use only (see `pyproject.toml`).

## 19. Deployment

The product ships as a thin FastAPI service (`product/backend_api/`) and a
Vite-built React frontend (`product/frontend/dist/`). Both are read-only
over the existing frozen Phase 19 artefacts; deployment never copies,
regenerates, or mutates research evidence.

### Prerequisites

- Python 3.11+ (the project ships a `.venv` at the repository root).
- Node.js 18+ and npm.
- uvicorn, fastapi, httpx (already installed in the venv).

### Backend (development)

```bash
.venv\Scripts\python.exe -m uvicorn product.backend_api.app.main:app --reload
```

Backend listens on `http://127.0.0.1:8000`. Swagger UI: `/docs`. OpenAPI:
`/openapi.json`. Health: `/health`.

### Frontend (development)

```bash
cd product/frontend
npm install
npm run dev
```

Frontend dev server listens on `http://127.0.0.1:5173`. The Vite dev
server proxies `/api` and `/health` to the backend at
`http://127.0.0.1:8000` (see `product/frontend/vite.config.ts`).

### Frontend (production build)

```bash
cd product/frontend
npm run build
```

The static bundle lands in `product/frontend/dist/`. To preview the
built bundle:

```bash
cd product/frontend
npm run preview
```

### Backend (production)

```bash
.venv\Scripts\python.exe -m uvicorn product.backend_api.app.main:app --host 0.0.0.0 --port 8000 --workers 1
```

For a single-host deployment, the production frontend can be served from
any static file host (nginx, Caddy, S3 + CloudFront) on the same
hostname as the backend, leaving `VITE_API_BASE_URL` unset so the
frontend uses the relative path `/api`.

For a multi-host deployment, rebuild the frontend with the backend
origin baked in:

```bash
cd product/frontend
set VITE_API_BASE_URL=https://api.example.com
npm run build
```

The frontend bundle then talks to `https://api.example.com/api/...`
without any runtime configuration.

### Environment variables

See `.env.example` for the full list. The variables are non-secret
deployment knobs (project root override, CORS allow-list, app
environment, frontend build-time API base). The product does NOT accept
LLM, quantum, or cloud credentials — adding `OPENAI_API_KEY` or
`QISKIT_TOKEN` would be a project-scope violation.

### Smoke test

```bash
.venv\Scripts\python.exe scripts/smoke_test_deployment.py --port 8765
```

Boots the FastAPI app in a real uvicorn worker, hits one endpoint per
router plus `/openapi.json`, and exits 0 when all probes succeed. Uses
the same product code as the test suite; not a second test framework.

### Tests

```bash
# Backend (513 tests)
.venv\Scripts\python.exe -m pytest

# Frontend (27 tests, ~5 s)
cd product/frontend
npm test

# TypeScript and production build
npx tsc -b
npm run build
```

### Why no Docker / no compose

The deployment surface is two artefacts: a Python process and a
static directory. Containerizing them would add a multi-stage build,
an image registry, and orchestration for two stateless containers
that share no volume and no network state. The current
`.venv + uvicorn + npm run build` workflow is reproducible, requires
no system services, and runs identically on any host that has Python
3.11+ and Node 18+.

The product is offline evaluation. There is no service that benefits
from a container runtime: no database (artefacts are static), no
message queue (no async work), no MLflow server (training is
complete), no LLM (agents are local-rule-based), no Redis (no
caching), no Kubernetes (single-host deployment is sufficient). Adding
these would be infrastructure theater, not reproducibility.

### Security headers

The API attaches `X-Content-Type-Options: nosniff`, `X-Frame-Options:
DENY`, and `Referrer-Policy: no-referrer` to every response. A CSP is
intentionally NOT set because FastAPI's `/docs` and `/redoc` use
inline scripts and styles; a strict CSP would break them.

### Non-goals

- No live telemetry, no streaming, no real-time monitoring.
- No autonomous agent execution; the agent layer is advisory only.
- No lifecycle mutation API. The 7 lifecycle action types
  (PROMOTE / DEPLOY / ROLLBACK / RETRAIN / CHANGE_POLICY /
  MODIFY_MODEL / MODIFY_FEATURES) are blocked by the agent firewall
  and the OpenAPI schema contains no path that maps to them.
- No live grid control, no production deployment, no cloud-scale
  MLOps, no AI-controlled deployment.
- No quantum / QML / GNN / LLM capability. The shipped code contains
  no such strings outside non-goal disclaimers.
- No secrets in the repository, no fake configuration knobs for
  services the product does not use.
