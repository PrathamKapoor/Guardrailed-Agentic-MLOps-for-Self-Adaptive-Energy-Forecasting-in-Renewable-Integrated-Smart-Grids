> **QUARANTINE NOTICE (2026-09-14).** Sections of this historical report claim
> "quantum-secure cryptography" and a "Quantum Trust Layer". Repository audits
> (reports/research_claim_audit.md, reports/agentic_research_claim_matrix.md)
> verified that **no executable code implements any of this**; the claims are
> foreign contamination from an unrelated quantum-derived document set. The
> canonical architecture is the classical pipeline described in
> docs/paper/system_architecture.md (rewritten 2026-09-14). Read the quantum
> passages below as non-normative foreign text.

# Phase 20 completion report

## Phase status

**PHASE 20 COMPLETE — final evaluation UI/UX (read-only evidence interface).**
No model files, predictions, governance state, protocol hashes, or model
registry state were modified. The 213-test pre-Phase-20 backend test suite
continues to pass (231 total tests now: 213 backend + 18 UI).

## UI architecture

Static single-page dashboard (`dashboard/index.html` + `dashboard/charts.html`)
plus a deterministic builder (`scripts/build_dashboard.py`) that reads the
authoritative Phase 19 evidence and emits static JSON snapshots under
`dashboard/data/`. The dashboard is served as static files; the builder is
the only file that touches Phase 19 artefacts, and it is read-only with
respect to them. No third-party frontend framework, no remote assets, no
build pipeline beyond `python scripts/build_dashboard.py`.

Detailed architecture: `docs/phase_20_ui_architecture.md`.

## Pages / views implemented

| Section | What it shows | Spec source |
| --- | --- | --- |
| Executive overview | Status, window, rows, folds, final-test access, configuration-frozen, headline findings, three target cards | spec § 8, § 9 |
| Performance table | Per-target MAE / RMSE / sMAPE / nMAE / nRMSE per configuration | spec § 10 |
| Benchmark comparison | Frozen model vs external benchmark per target with absolute / relative difference and result indicator | spec § 14 |
| Actual vs predicted | Embedded existing Phase 19 figure + interactive canvas chart on `charts.html` with date-range filter | spec § 11 |
| Error analysis | Per-target mean / median / P95 / mean signed error per configuration (derived from final predictions) + embedded error distribution figure | spec § 12 |
| Target comparison | Three-target comparison across MAE, RMSE, sMAPE, nMAE, nRMSE | spec § 13 |
| Model details | Per-target model family, feature set, frozen registry identity, frozen status | spec § 15 |
| Feature details | Per-feature meaning (lag_1 = previous hour; lag_24 = previous day; lag_168 = previous week) | spec § 16 |
| Evaluation protocol | Window, rows per target, F11 / F12, final-test access authorization, NO training / HPO / feature selection / model selection / retraining | spec § 17 |
| Lineage | Phase 10 → 11 → 13/15/16 → 17 → 19 → 20 chain + model/feature/dataset fingerprints + raw lineage report | spec § 19 |
| Governance | model_promoted 0, challengers_created 0, governance_state_changes 0, rollback_events 0, protocol_checksums PASS, agent_package UNCHANGED | spec § 20 |
| Agent safety / evidence boundary | REPORT_GENERATION_AGENT and EVIDENCE_RETRIEVAL_AGENT may explain; cannot modify final models | spec § 21 |
| Audit | Tests, compile, RTS, freeze checksums, frozen plan SHA-256, Phase 19 protocol freeze SHA-256, raw audit JSON, raw completion report | spec § 22 |
| Artifact explorer | Nine primary artefacts (paths + descriptions) | spec § 30 |
| Limitations | Evaluation covers the locked test period, benchmark comparisons are target-specific, performance varies, final models are frozen, no further optimization, UI is read-only, conclusions scoped | spec § 40 |

## Data sources (read-only)

`scripts/build_dashboard.py` reads from:

- `artifacts/research_tables/final_predictions.csv` (13,176 rows; 1464 hourly points × 3 configurations × 3 targets)
- `artifacts/research_tables/final_forecasting_results.csv`
- `artifacts/research_tables/final_model_comparison.csv`
- `artifacts/audit/phase_19_final_execution_audit.json`
- `artifacts/mlops/lineage/final_evaluation_lineage_report.md`
- `artifacts/experimental_design/phase_19_final_evaluation_protocol_freeze.yaml`
- `artifacts/experimental_design/final_test_comparison_plan.yaml`
- `artifacts/research_figures/phase_19/{final_model_performance_comparison.png, final_error_distribution.png, forecast_vs_actual_plots.png, system_architecture_final.svg}`
- `reports/phase_19_completion.md`

`scripts/build_dashboard.py` writes to:

- `dashboard/index.html` (verified, no changes)
- `dashboard/charts.html` (verified, no changes)
- `dashboard/styles.css` (verified, no changes)
- `dashboard/app.js` (verified, no changes)
- `dashboard/data/results.json`
- `dashboard/data/predictions.json`
- `dashboard/data/protocol.json`
- `dashboard/data/lineage.json`
- `dashboard/data/figures.js`

`artifacts/ui_build/phase19_integrity_baseline.json` is written once at the
start of Phase 20 to record the pre-UI Phase 19 SHA-256 state.

## Evidence mapping

Every number displayed in the UI comes from one of the Phase 19 artefacts
above. There is no model result computed or invented in the browser. The
test `test_dashboard_does_not_modify_phase19_artefacts` re-runs the builder
and verifies that the bytes of every Phase 19 artefact are unchanged.

## Tests

`tests/test_phase20_dashboard.py` — **18 tests**, all passing.

| # | Test | What it asserts |
| --- | --- | --- |
| 1 | `test_all_required_files_exist` | Every dashboard file is present |
| 2 | `test_required_phase19_artifacts_present` | Every Phase 19 source is present |
| 3 | `test_figures_data_uri_well_formed` | The four figures are embedded as base64 data URIs |
| 4 | `test_target_switch_clean_per_target` | No per-target field bleeds across targets |
| 5 | `test_per_target_model_uses_correct_identity` | LOAD=RF, WIND=HistGB, PV=RF; registry identity preserved exactly |
| 6 | `test_evaluation_window_matches_protocol` | Window = 2020-11-01 → 2020-12-31, 1464 hours |
| 7 | `test_predictions_row_counts` | 1464 × 3 per target |
| 8 | `test_frozen_status_pass_and_no_training_messages_present` | F11/F12, FROZEN markers, NO-training/HPO/feature selection/model selection/retraining labels |
| 9 | `test_frozen_load_text_present` | "Lower MAE is better"; honest interpretation for PV (better) and LOAD/WIND (worse) |
| 10 | `test_governance_invariants_in_data` | All four governance counters = 0 |
| 11 | `test_no_secrets_in_html` | No api_key / secret / password / sk- / AKIA tokens |
| 12 | `test_no_writable_button_in_html` | No run-training / tune / select-features / promote / rerun controls |
| 13 | `test_chart_uses_canvas_no_third_party_network_calls` | No https URLs, no CDN, canvas element present |
| 14 | `test_cross_target_consistency_in_data` | LOAD uses LOAD model, WIND uses WIND model, PV uses PV model (spec § 33) |
| 15 | `test_protocol_freeze_sha_recorded_in_ui_data` | Recorded SHA-256 matches the YAML file and the integrity baseline |
| 16 | `test_dashboard_does_not_modify_phase19_artefacts` | Re-running the builder leaves every Phase 19 file byte-identical |
| 17 | `test_no_placeholders_in_html` | No `TODO` / `FIXME` / `placeholder` strings |
| 18 | `test_dashboard_accessibility_minimums` | Skip-link, ARIA roles, focus styles, non-color indicator helpers, chart role/aria-label |

## Production build status

- `.venv\Scripts\python.exe scripts/build_dashboard.py`: **PASS** (writes 9 files; exits 0)
- `.venv\Scripts\python.exe -m compileall -q src scripts tests dashboard`: **PASS**
- All static assets served from `dashboard/index.html` and `dashboard/charts.html`

## Artifact integrity verification (spec § 47)

Recorded at the start of Phase 20 in
`artifacts/ui_build/phase19_integrity_baseline.json` for 20 critical artefacts,
then re-verified at the end of Phase 20. **All 20 artefacts remained
byte-identical**:

```
intact: artifacts/research_tables/final_predictions.csv
intact: artifacts/research_tables/final_forecasting_results.csv
intact: artifacts/research_tables/final_model_comparison.csv
intact: artifacts/audit/phase_19_final_execution_audit.json
intact: artifacts/mlops/lineage/final_evaluation_lineage_report.md
intact: artifacts/research_figures/phase_19/final_model_performance_comparison.png
intact: artifacts/research_figures/phase_19/final_error_distribution.png
intact: artifacts/research_figures/phase_19/forecast_vs_actual_plots.png
intact: artifacts/research_figures/phase_19/system_architecture_final.svg
intact: artifacts/experimental_design/phase_19_final_evaluation_protocol_freeze.yaml
intact: artifacts/experimental_design/phase_10_ablation_protocol_freeze.yaml
intact: artifacts/experimental_design/final_test_comparison_plan.yaml
intact: artifacts/model_registry/lifecycle_registry.yaml
intact: artifacts/model_registry/forecasting_reference_registry.yaml
intact: config/governance/phase_13_policy.yaml
intact: config/retraining/phase_15_policy.yaml
intact: config/governance/phase_16_promotion_policy.yaml
intact: reports/phase_19_completion.md
intact: src/smartgrid_mlops/agents/schemas.py
intact: src/smartgrid_mlops/agents/firewall.py
```

## Security review (spec § 38)

- No API keys, credentials, secrets, tokens, or private filesystem paths exposed in the HTML / JS / CSS / JSON snapshots.
- No environment variables or internal infrastructure exposed.
- No remote URLs, no third-party CDN links, no `https://` calls.
- The dashboard is a research evidence interface only.

## Performance observations

- `dashboard/data/predictions.json` is 3.16 MB (13,176 rows). The client parses it once, then re-filters per target / date range in-memory.
- `dashboard/data/figures.js` is 470 KB (base64-encoded PNGs/SVG). Acceptable for an offline research demo; future deployments could split or lazy-load the figures.
- `dashboard/index.html`, `styles.css`, `app.js`, `data/*.json` are all served as flat static files; no server-side rendering, no database, no authentication.

## Screens / views implemented

`index.html` (12 anchor sections): executive overview, target cards, performance, benchmark, forecast vs actual, error analysis, model details, feature details, evaluation protocol, lineage, governance, audit, artifacts, limitations.

`charts.html`: interactive Actual-vs-Predicted chart with date-range filter, canvas rendering, legend, axis labels. Returns to the dashboard via a header link.

## Known limitations

- The dashboard is a single static page; deeper drill-down into individual MLflow runs is via the `<details>` raw-JSON view in the audit section, not via an interactive browser.
- The interactive chart is a custom canvas implementation; advanced features (per-point tooltips, crosshair zoom) are not implemented. The underlying hourly values are available — a reviewer who wants per-point detail can open the raw `final_predictions.csv`.
- The dashboard is designed for desktop-first research review; mobile is supported but not the primary target.
- Phase 20 is downstream of Phase 19; any future re-run of Phase 19 would require a rebuild via `scripts/build_dashboard.py` to refresh the static snapshots.

## Phase 19 evidence was not modified (spec § 18)

All 20 critical artefacts in the integrity baseline remain byte-identical
to their pre-Phase-20 state. The only Phase-20-added file under `artifacts/`
is the integrity baseline itself (`artifacts/ui_build/phase19_integrity_baseline.json`),
which is a Phase 20 artefact (not a Phase 19 modification).

## No models were modified (spec § 17)

No training, HPO, feature selection, model selection, or retraining was
performed in Phase 20. The frozen model files under `artifacts/model_registry/`
and the policy files under `config/` are unchanged.

## Recommended next phase

This is the final phase of the research project. No further development is
required. The final research evidence package consists of:

- 20 protocol freeze artefacts (all verified PASS)
- Phase 0–19 completion reports
- The frozen Phase 19 final evaluation evidence
- The Phase 20 read-only evidence interface

A future package could package `dashboard/` as a Docker container with
`python -m http.server` for hosting, but the static site has no
runtime dependencies beyond a browser.
