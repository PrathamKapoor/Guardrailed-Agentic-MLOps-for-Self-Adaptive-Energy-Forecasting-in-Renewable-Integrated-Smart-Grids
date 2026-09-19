# Changelog

All notable changes to the smartgrid-mlops research platform are documented
here. The canonical phase-by-phase record is `reports/phase_*_completion.md`;
this file summarizes user-visible and structural changes only.

## [0.20.0] - 2026-09-14
### Added
- Product layer: FastAPI evidence API (17 read-only routes) and React console;
  live research console for user-registered datasets and local chronological
  forecasting runs (manifests recorded before first use).
- Optional bearer-token auth on /api routes (SMARTGRID_MLOPS_API_TOKEN).
- Docker image + compose files; GitHub Actions CI (pytest + frontend).
- requirements.txt (pinned) and .env for local configuration.
- Final-evaluation verification entry point (run_final_evaluation.py).

### Changed
- Environment-variable prefix renamed QSMLOPS_* -> SMARTGRID_MLOPS_*
  (legacy names still honored as fallback in product config and replay script).
- API/package version aligned at 0.20.0; product.backend_api now ships in the wheel.

### Fixed
- Quantum "Trust Layer" contamination in docs/paper removed; the drafts now
  describe the actual classical system (rewritten from repository artifacts).
- Frontend health check called /api/health (404); now calls /health.
- Silent metric-parse failures in the historical importer are now recorded on
  the imported record.

## [0.1.0] - 2026-08/09 (Phases 00-19)
- Data ingestion and checksummed RTS-GMLC manifests; feature pipelines;
  classical + neural experiments with rolling-origin validation; Phase 11
  finalist selection; Phase 13 governance policy and engine; Phase 19 protocol
  freeze and single final evaluation (artifacts under artifacts/research_tables
  and artifacts/final_release); drift monitoring research (Stages 07-14);
  honest 7/7 governance DENY outcome recorded.