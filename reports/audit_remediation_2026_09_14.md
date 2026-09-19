# Audit Remediation Report — 2026-09-14

Scope: the 46-item audit list (7 critical, 13 high, 15 medium, 11 low), actioned in order.
Ground rules: frozen artifacts untouched (Phase 13 policy, Phase 19 protocol freeze);
honest results are reported, never altered; historical audit reports preserved as evidence.

## CRITICAL

| # | Item | Disposition |
|---|---|---|
| 1 | Quantum contamination in docs | **FIXED.** `docs/paper/*` (11 files) rewritten to describe the actual classical system (RTS-GMLC, frozen results, Phase 13 governance, 7/7 DENY) — this resolves the quarantine the repo's own audits had placed on those files. `artifacts/final_release/architecture_diagram.svg` replaced with an honest 5-layer diagram. `reports/phase_20_completion.md` carries a quarantine banner. `handoff.md` quarantine note updated. Remaining mentions in `reports/*.md` are historical audit evidence; `docs/paper/introduction.md` keeps only the standard "no quantum/GNN/LLM" disclaimer. |
| 2 | "LLM agent is a fake" | **DISPOSITION: by design, documented.** Project policy excludes LLMs; `LLMBackendInterface` is an explicitly optional contract ("no implementation is provided or required"). `agents/base.py` docstrings clarified: `LocalRuleBackend` is the designed production path, not a placeholder. |
| 3 | run_final_evaluation.py incomplete | **FIXED.** Rewritten as a read-only verification entry point: recomputes MAE/RMSE/sMAPE/nMAE/nRMSE from the sealed `final_predictions.csv` using the canonical metrics module and cross-checks the recorded results. Verifies 9/9 groups; deliberately does NOT re-run inference (protocol integrity). Canonical runner remains `scripts/run_phase19_final_evaluation.py`. |
| 4 | Models lose to baselines (2/3) | **DISPOSITION: honest result, not a defect.** Reported in README, `docs/paper/results.md`, and the sealed CSVs; no numbers changed. |
| 5 | docker/ empty | **FIXED.** `docker/Dockerfile` (slim Python image serving the API with sealed artifacts) and `docker/docker-compose.yml` (api + frontend dev server, healthcheck). |
| 6 | Undeclared dependencies | **FIXED.** pyproject now declares numpy, fastapi, uvicorn, starlette, pydantic, python-multipart, pyyaml, httpx alongside the originals; `dev` extra added. |
| 7 | QSMLOPS naming | **FIXED.** Env prefix renamed to `SMARTGRID_MLOPS_*` with legacy `QSMLOPS_*` fallback in product config and `scripts/replay_telemetry.py`; loggers renamed `smartgrid_mlops.api.*`; README/.env.example updated. |

## HIGH

| # | Item | Disposition |
|---|---|---|
| 8 | No requirements.txt | **FIXED.** Pinned `requirements.txt` generated from the working venv (21 pins). |
| 9 | Version 0.0.0 | **FIXED.** Package version `0.20.0` (20 phases). |
| 10 | Stale `__init__` docstring | **FIXED.** Describes the actual platform. |
| 11 | No CI | **FIXED.** `.github/workflows/ci.yml`: pytest + artifact verification + frontend (tsc/vitest/build). |
| 12 | No API auth | **FIXED (opt-in).** Bearer-token middleware on `/api` routes, enabled by `SMARTGRID_MLOPS_API_TOKEN`; default off (documented: read-only API, research writes confined to `artifacts/research_ui/`). |
| 13 | Silent except in importer | **FIXED.** Unparsable metric cells recorded as `unparsable_metric_fields` on the imported record. |
| 14 | product/ not in wheel | **FIXED.** `product/__init__.py` + `product/backend_api/__init__.py` added; hatch packages include `product`. |
| 15 | No .env | **FIXED.** `.env` created from `.env.example` with local defaults. |
| 16 | print() in scripts | **DEFERRED.** 46 standalone phase scripts; conversion is mechanical churn with low risk-adjusted value while phase reports record their outputs. Library and API code already use logging. |
| 17 | notebooks/ empty | **DEFERRED.** Research is script+report based; nothing fabricated to fill it. |
| 18 | models/ empty | **DEFERRED.** Frozen models live in the registry/artifacts under the Phase 19 freeze; re-serializing into `models/` would require a governed re-run. |
| 19 | External validation fails | **DISPOSITION: honest result.** Documented in `docs/paper/limitations.md` (item 1) — frozen models transfer poorly to OPSD; not a code fix. |
| 20 | demo_core.py missing | **STALE AUDIT CLAIM.** No reference to `demo_core.py` exists in docs/ or scripts/ (grep verified); nothing to create. |

## MEDIUM

| # | Item | Disposition |
|---|---|---|
| 21 | Duplicate imports | **FIXED.** File rewritten; single clean import block. |
| 22 | QSMLOPS vs smartgrid_mlops | **FIXED** (see #7). |
| 23 | Pass-only exception classes | **FIXED.** Self-describing default messages on all six `ExternalValidationError` subclasses. |
| 24 | protocol.py stub | **FIXED.** `ProtocolAccessError` documents and carries the protocol boundary message. |
| 25 | HPO 5 trials | **PARTIALLY FIXED.** `SMARTGRID_MLOPS_HPO_TRIALS` env knob added (default 5). Changing the default would alter recorded experiment provenance; more trials require a governed re-run. |
| 26 | Seed 42 hardcoded | **DISPOSITION: deliberate.** Pinned by the Phase 19 protocol freeze (`seed_hard_coded_in_implementation`); changing it would break reproducibility of recorded results. |
| 27 | Stale phase-report refs | **DEFERRED.** Phase reports are historical records; retro-editing them would undermine their evidentiary value. |
| 28 | No type checking config | **FIXED.** `[tool.mypy]` added (library-targeted, scripts excluded, rationale documented). |
| 29 | Dashboard pre-baked | **DISPOSITION: by design.** Offline evidence snapshots; the live research console adds real runs without mutating the frozen evidence. |
| 30 | dist/ committed | **FIXED.** Deleted (rebuilt via `npm run build`); gitignored. |
| 31 | node_modules committed | **PARTIALLY FIXED.** Gitignored; not deleted from the working tree (dev server depends on it). |
| 32 | License inconsistency | **FIXED.** `LICENSE` added (proprietary research license; notes third-party licenses and RTS-GMLC provenance). |
| 33 | No linting config | **FIXED.** `[tool.ruff]` added with pragmatic defaults. |
| 34 | API version mismatch | **FIXED.** `api_version` aligned to 0.20.0. |
| 35 | _prev_paper_text.txt | **FIXED.** Deleted (was a scratch file from the paper-style reference extraction). |

## LOW

| # | Item | Disposition |
|---|---|---|
| 36 | .gitignore thin | **FIXED.** Node/dist/build/caches/log patterns added. |
| 37 | __pycache__ committed | **FIXED.** 36 directories removed; gitignored. |
| 38/39 | Script naming / no CLI framework | **DEFERRED.** Cross-cutting refactor of 46 historical phase scripts; low value vs. risk while scripts are one-shot and their outputs are recorded. |
| 40 | RegistrationError one-liner | **DEFERRED.** Idiomatic Python; a subclass with no added state needs no body. |
| 41 | No source maps | **FIXED.** Vite `build.sourcemap: true`. |
| 42 | data/raw vs data/external | **FIXED.** `data/README.md` documents both locations and which one the pipeline reads. |
| 43 | Redundant return in LocalRuleBackend | **FIXED.** Documented as the intentional deterministic fallback (see #2). |
| 44 | Phase 09 deviations unresolved | **DEFERRED.** The deviation reports are the record; no code path depends on them. |
| 45 | No CHANGELOG | **FIXED.** `CHANGELOG.md` with 0.20.0 and 0.1.0 (Phases 00–19) summaries. |
| 46 | No LICENSE file | **FIXED** (see #32). |

## Verification

- Backend: full pytest suite green (the two failures surfaced during remediation were a README quick-start placement required by `test_hackathon_readiness`; fixed and re-verified, including the nested full-suite run).
- Frontend: 27/27 vitest, tsc clean, production build OK (now with source maps).
- `run_final_evaluation.py`: 9/9 sealed groups verify.
- API restarted on the renamed config: `/health` 200 direct and proxied; research datasets endpoint live.


## Round 2 (2026-09-14, continued) — previously deferred items

| # | Item | Disposition |
|---|---|---|
| 16 | print() in scripts | **FIXED.** 141 human-progress prints converted to `LOGGER.info` across 37 scripts, with `logging.basicConfig(stream=sys.stderr)` per script; 30 machine-readable protocol lines (JSON summaries, `KEY=value` lines) deliberately kept on stdout — they are parsed output and documented as such in `scripts/README.md`. Note: a parallel `_scriptlog` logging helper landed in 6 scripts concurrently; its stdout-preserving logger was kept, double-logging reconciled, and its broken `from __future__` ordering repaired. Two CLI stdout contracts asserted by tests (`replay_telemetry.py`, `run_incremental_monitoring.py`) were restored to `print` per the documented stdout contract. All 46 scripts now pass `py_compile` (which, unlike `ast.parse`, enforces `__future__` placement). |
| 17 | notebooks/ empty | **FIXED.** `notebooks/01_rts_gmlc_overview.ipynb`: read-only dataset overview + sealed results table. |
| 18 | models/ empty | **FIXED.** `models/README.md` documents where frozen models actually live (registry/MLflow artifacts) and why re-serialization is governed. |
| 27 | Stale phase-report refs | **FIXED (measured, not edited).** `scripts`-level checker run: 680 path references scanned, 29 broken recorded in `reports/audits/phase_report_reference_check.md`. History not retro-edited. |
| 38/39 | Script naming / CLI | **PARTIALLY FIXED.** `scripts/README.md` documents the naming convention (`run_`/`build_`/`finalize_`/`select_`/...) and indexes all 46 scripts with the logging/stdout contract. Mass renames and argparse retrofits remain deferred (they would break recorded command lines in phase reports). |
| 40 | RegistrationError one-liner | **FIXED.** Self-describing default message, matching the other typed errors. |
| 44 | Phase 09 deviations unresolved | **STALE AUDIT CLAIM.** Both deviation reports already carry `Status: RESOLVED` headers; no action needed. |

### Round 2 verification
- 46/46 scripts compile (`py_compile`).
- Full backend suite: exit 0 (all tests pass, including the nested pre-freeze full-suite re-run).
- Frontend unchanged: 27/27 tests, build OK.

## Deliberately not done (with reasons)

- No result numbers changed anywhere; negative benchmark outcomes and the external-validation failure remain honestly reported.
- Frozen artifacts (Phase 13 policy YAML, Phase 19 freeze) untouched.
- print→logging, script CLI framework, notebooks/, models/ population, and phase-report retro-edits deferred with dispositions above.
