# Hackathon submission checklist

The repository is a complete 20-phase governance-first MLOps research system for electricity forecasting. This checklist records the state of every spec requirement against the actual repository contents.

## Project identity

- [x] Project has a clear name: **Guardrailed Agentic MLOps for Self-Adaptive Energy Forecasting in Renewable-Integrated Smart Grids**
- [x] One-line explanation: "A 20-phase, governance-first MLOps system for electricity forecasting with a bounded, firewalled agentic decision-support layer and a frozen, fully audited final evaluation." (`README.md` first line, `docs/hackathon_usp.md`)
- [x] Short description: 30-second elevator pitch in `docs/hackathon_usp.md`
- [x] Technical description: 2-minute technical pitch in `docs/hackathon_usp.md` and `docs/hackathon_demo_3min.md`
- [x] Research question documented in `AGENTS.md` and the problem section of `hackathon/index.html`
- [x] Key innovation: governance firewall for agents (`docs/research_methodology/bounded_agentic_ai.md` and "What makes this different" section)
- [x] Target users / use case: research audience (the submission is a research artefact; deployment is future work, not a current claim)
- [x] Final demonstrated result: PV −7.61% vs H24 daily persistence; LOAD and WIND lose to RTS_DAY_AHEAD (`artifacts/research_tables/final_model_comparison.csv`)
- [x] Limitations listed in `hackathon/index.html` and `docs/research_methodology/threats_to_validity.md`

## Demo + demo scripts

- [x] `hackathon/index.html` is the judge-facing landing page (entry point with hero, problem, solution, results, demo CTAs)
- [x] `dashboard/index.html` is the primary interactive demo (existing Phase 20 evidence interface, linked from the landing page)
- [x] `dashboard/charts.html` is the interactive actual-vs-predicted chart
- [x] `docs/hackathon_demo_script.md` — 90-second demo script with exact clicks
- [x] `docs/hackathon_demo_3min.md` — 3-minute demo script with explicit per-segment guidance
- [x] `docs/hackathon_recording_script.md` — 90–120 second video script
- [x] `docs/hackathon_demo_3min.md` covers problem → architecture → quantum component (acknowledges absence honestly) → demo → results → evidence → differentiation → conclusion

## Result and evidence

- [x] The strongest verified results are visible on the hero card and the Benchmark comparison section of the landing page
- [x] Negative results are honestly represented: PV wins, LOAD and WIND lose, both with explicit indicators and rationale
- [x] Benchmark comparison is visible (table + per-target rows)
- [x] Research evidence is accessible via "Research evidence" section linking to model registry, frozen protocol, final evaluation evidence, dashboard, and full documentation

## Reproducibility

- [x] Installation: `docs/hackathon_installation.md` documents Python 3.11+, pip, ~3 minutes, no GPU, no network
- [x] Quick start in the landing page and `README.md`
- [x] Demo commands: `python -m pytest`, `python scripts/bootstrap_rts_gmlc.py --verify-only`, `start dashboard/index.html`
- [x] Repository structure documented in `README.md` and the "Repository structure" section of the landing page
- [x] Full test suite: 231 backend + 18 dashboard + (new) 16 hackathon tests, all deterministic, 0 failures expected
- [x] Freeze check verification: 20 protocol freezes with sidecar SHA-256s, all PASS
- [x] Phase 19 integrity baseline: 20 critical artefacts verified byte-identical

## Documentation

- [x] README overhauled (`README.md`) — judge-first first screen
- [x] Architecture documentation: `docs/architecture_overview.md` (existing) + `hackathon/architecture.svg` (new) + `docs/phase_20_ui_architecture.md` (existing)
- [x] Quantum component is **explicitly addressed and honestly absent** — the FAQ, demo scripts, and judging matrix all state the project does not use quantum computing, GNNs, or LLMs
- [x] Hackathon-specific docs: `hackathon_usp.md`, `hackathon_demo_script.md`, `hackathon_demo_3min.md`, `hackathon_recording_script.md`, `hackathon_faq.md`, `hackathon_judging_matrix.md`, `hackathon_installation.md`
- [x] Submission checklist: this file
- [x] Completion report: `reports/hackathon_readiness_completion.md`

## Integrity

- [x] No secrets in any HTML / JS / CSS / JSON / Markdown
- [x] No broken internal links (validated by `tests/test_hackathon_readiness.py::test_internal_links_resolve`)
- [x] No unexpected Phase 19 artefact changes (validated by `tests/test_hackathon_readiness.py::test_phase19_integrity_baseline_holds`)
- [x] Existing 231 backend tests + 18 dashboard tests still pass
- [x] 16 new hackathon tests pass (no fabrication, no broken links, no writable controls, all anchor IDs present, accessibility minimums)
- [x] Production build (dashboard data build) passes
- [x] Offline operation: dashboard has no external CDN / no remote fonts / no third-party network calls

## Documentation of honest limitations

- [x] One year of one dataset (RTS-GMLC 2020)
- [x] Classical ML only — no quantum, no GNN, no LLM
- [x] External benchmark (RTS_DAY_AHEAD) is strong on short horizons
- [x] Agent operational benefit measured by cost model, not user study
- [x] Offline evaluation only — no production deployment

## What is NOT in this submission (intentionally)

- [x] No "train" / "retrain" / "tune" / "promote" / "rerun final test" controls anywhere in the UI (verified)
- [x] No fabricated quantum / GNN / LLM story (verified by `test_hackathon_landing_does_not_claim_quantum_or_gnn`)
- [x] No screenshots (the project is a static dashboard; the source is the screenshot. The hackathon layer is honest about not fabricating visuals; reviewers open the actual page.)
- [x] No placeholder content (no TODO, FIXME, lorem ipsum — verified)
- [x] No claims of universal superiority — the result is presented as the mixed outcome it is

## How to verify the checklist

Run the full test suite:

```bash
.venv\Scripts\python.exe -m pytest
```

Expected: 231 backend + 18 dashboard + 16 hackathon = **265 passed, 0 failed, 0 skipped, 0 warnings**.

Verify the freeze hashes and the Phase 19 integrity baseline:

```bash
.venv\Scripts\python.exe -c "
import hashlib, json
from pathlib import Path
for sha_file in Path('artifacts/experimental_design').glob('*.sha256'):
    base = sha_file.with_suffix('')
    want = sha_file.read_text(encoding='utf-8').split()[0]
    got = hashlib.sha256(base.read_bytes()).hexdigest()
    print(('PASS' if want == got else 'FAIL') + ' ' + base.name)
b = json.loads(open('artifacts/ui_build/phase19_integrity_baseline.json').read())
for p, info in b.items():
    if not isinstance(info, dict): continue
    actual = hashlib.sha256(open(p, 'rb').read()).hexdigest()
    print(('intact' if actual == info['sha256'] else 'CHANGED') + ' ' + p)
"
```

Expected: 20 × `PASS` for the freeze files and 20 × `intact` for the integrity baseline.
