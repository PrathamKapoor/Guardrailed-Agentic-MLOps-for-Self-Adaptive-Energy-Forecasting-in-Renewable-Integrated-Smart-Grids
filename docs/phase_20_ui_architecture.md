# Phase 20 UI architecture

## Purpose

Phase 20 is the final UI/UX and evidence-presentation layer for the completed
Phase 19 final evaluation. It is strictly read-only: it consumes the Phase 19
artefacts and renders them faithfully. It does not generate new model
evidence, does not modify the models, and does not influence the frozen
final evaluation in any way.

## Data sources (all read-only)

The dashboard is built once by `scripts/build_dashboard.py` from the
authoritative Phase 19 artefacts:

- `artifacts/research_tables/final_predictions.csv` → `dashboard/data/predictions.json` (per-row predictions; 13177 rows; 1464 hourly points × 3 configurations × 3 targets)
- `artifacts/research_tables/final_forecasting_results.csv` → `dashboard/data/results.json` (per-target MAE/RMSE/sMAPE/nMAE/nRMSE per configuration)
- `artifacts/research_tables/final_model_comparison.csv` → `dashboard/data/results.json` (frozen model vs external benchmark per target)
- `artifacts/audit/phase_19_final_execution_audit.json` → `dashboard/data/results.json` and `lineage.json` (governance invariants, access log, fingerprints)
- `artifacts/mlops/lineage/final_evaluation_lineage_report.md` → `dashboard/data/lineage.json`
- `artifacts/experimental_design/phase_19_final_evaluation_protocol_freeze.yaml` → `dashboard/data/protocol.json` (frozen models, baselines, features, protocol SHA-256)
- `artifacts/experimental_design/final_test_comparison_plan.yaml` → `dashboard/data/protocol.json`
- `artifacts/research_figures/phase_19/*.{png,svg}` → embedded as base64 in `dashboard/data/figures.js`
- `reports/phase_19_completion.md` → `dashboard/data/lineage.json` (raw markdown)
- `artifacts/ui_build/phase19_integrity_baseline.json` (Phase 19 integrity baseline; recorded BEFORE the UI build, compared AFTER)

## Read-only boundary

- `dashboard/` is the only directory the build script writes to.
- The build script never opens any artefact in `artifacts/`, `config/`, `data/`, `reports/`, or `src/` for writing.
- The HTML pages link only to local static assets under `dashboard/`. No remote URLs, no third-party CDNs, no external API calls.
- The build script reads Phase 19 artefacts but does not parse or summarise them in a way that re-derives numbers; all numbers displayed in the UI come directly from the authoritative artefacts (either as numbers in JSON, or as base64-encoded bytes of an existing PNG figure).
- The build script does not write any new artefact into `artifacts/`. The one file under `artifacts/` produced by the build is `artifacts/ui_build/phase19_integrity_baseline.json` (a SHA manifest of the pre-UI Phase 19 state, written once at the start of Phase 20). This file is itself an artefact of Phase 20 and is not a Phase 19 modification.

## Component architecture

| File | Role |
| --- | --- |
| `dashboard/index.html` | Single-page executive + research dashboard with anchor sections for every required topic |
| `dashboard/charts.html` | Interactive Actual-vs-Predicted chart with date-range controls, zoom-equivalent line plot (canvas, no third-party chart library) |
| `dashboard/styles.css` | Restrained research aesthetic, dark theme, non-color indicators, accessible focus styles, responsive breakpoint at 700px |
| `dashboard/app.js` | Read-only client: fetches `data/*.json`, validates the data contract (spec section 32), renders every section, binds target-selection tabs |
| `dashboard/data/results.json` | Per-target metrics + model-vs-benchmark + governance invariants |
| `dashboard/data/predictions.json` | Long-format predictions used by the error analysis and charts pages |
| `dashboard/data/protocol.json` | Frozen models, baselines, features, evaluation window, protocol SHA-256 |
| `dashboard/data/lineage.json` | Lineage narrative + completion report + raw audit JSON |
| `dashboard/data/figures.js` | Embedded base64 of the four existing Phase 19 PNG/SVG figures |
| `scripts/build_dashboard.py` | The single read-only builder; never writes to Phase 19 artefacts |

## Evidence mapping

Each piece of UI evidence is traceable to a specific source file. Examples:

- The "LOAD random_forest MAE 174.26" card → `final_forecasting_results.csv` row where target=load and Model=random_forest → `dashboard/data/results.json` → `index.html#cardGrid` rendered by `app.js#renderTargetCards`.
- The "Phase 19 protocol freeze VERIFIED" line → `final_evaluation_protocol_freeze.yaml` SHA-256 → `protocol.json` → `index.html` audit panel.
- The four existing Phase 19 PNG figures → embedded in `figures.js` → rendered by `index.html#forecastFigure` / `#errorFigure`.

## Target mapping (cross-target consistency)

Spec section 33 requires that LOAD uses the LOAD model, WIND uses the WIND model, and PV uses the PV model — and that switching targets does not leak values from another target. The dashboard enforces this through:

1. The data layer keys all results and predictions by target, so a per-target lookup cannot accidentally return another target's data.
2. The `target-btn` click handler explicitly resets the state and re-renders only the target-derived panels (target cards, model details, feature details).
3. The test `test_cross_target_consistency_in_data` verifies that for each target the model identity in `results.json` matches the model used in the predictions stream, and that the frozen registry identity (`P10-{target}-{model}-B_lags_only`) is preserved exactly.
4. The test `test_per_target_model_uses_correct_identity` verifies that each target's frozen model matches the registered one and the registry identity is correct.

## Visualization strategy

- Existing Phase 19 figures (embedded as base64) are shown unchanged, with their original titles/labels preserved.
- Error analysis views are derived deterministically from the long-format predictions (mean / median / P95 absolute error, mean signed error). They are clearly labelled "derived from final predictions" (spec section 12).
- The interactive actual-vs-predicted chart is a custom canvas implementation (no third-party charting library required) with date-range controls that only re-filter the in-memory array, never the source.
- Per-target comparisons are shown side-by-side with a non-color status indicator (better / worse / flat dot before the metric) for accessibility (spec section 25).

## Security boundary

- The UI never exposes API keys, secrets, tokens, credentials, private filesystem paths, or environment variables (test `test_no_secrets_in_html` enforces this).
- The UI is a research evidence interface, not a control surface. No button or form can mutate predictions, metrics, model configuration, registry, governance, protocol hashes, or audit logs.
- Forbidden actions: training, retraining, HPO, feature selection, model selection, promotion, challenger creation (test `test_no_writable_button_in_html`).

## Testing strategy

`tests/test_phase20_dashboard.py` covers:

- File presence: every required dashboard file exists; every required Phase 19 artefact exists.
- Data contract: results/predictions/protocol/lineage JSON validates; the four figures are embedded as base64 data URIs; the protocol freeze SHA-256 matches the YAML file and the integrity baseline.
- Cross-target consistency: each target uses the correct frozen model and benchmark; the registry identity is preserved exactly; the per-target prediction stream uses the expected model; row counts are exactly 1464 × 3 per target.
- UI content: the page displays the no-training / no-HPO / no-retraining guarantee; the fold labels (F11, F12); the FROZEN/PASS markers; the lag-feature explanations; the final-test "AUTHORIZED FOR INFERENCE ONLY" header; and an honest result interpretation (PV beats the benchmark; LOAD and WIND do not).
- Read-only boundary: the build script does not modify any Phase 19 artefact; the dashboard contains no secrets, no remote URLs, no third-party CDN links.
- Accessibility: skip-link, ARIA roles, aria-* attributes, focus outline styles, chart role/aria-label, non-color indicator helpers.
- Forbidden content: no `TODO` / `FIXME` placeholders, no training-related controls.

## Production build status

The "build" for this dashboard is `python scripts/build_dashboard.py`. The
script is deterministic, idempotent, and exits 0 on success. It reads from
the Phase 19 evidence directory and writes only into `dashboard/`. It
performs no network access and no model training. The static assets are
served from `dashboard/index.html` and `dashboard/charts.html`.

## Phase 20 does not generate new model evidence

- No predictions are recomputed.
- No metrics are re-derived (existing numbers are copied verbatim from the Phase 19 CSVs).
- No model is retrained.
- No policy is changed.
- No agent is modified.
- No Phase 19 artefact is overwritten.
- No freeze checksum is changed.

The integrity baseline recorded in `artifacts/ui_build/phase19_integrity_baseline.json` (20 artefacts) is verified to remain byte-identical to the post-UI-build state, with all 20 freeze checksums passing.
