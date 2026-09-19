# Hackathon judging matrix

The repository is mapped to common judging categories. For each category, the claim is grounded in a recorded artefact; the evidence column points to the file or page that proves the claim; "where to demonstrate" points to the part of the demo the judge should see.

| Category | Claim | Evidence | Where to demonstrate |
| --- | --- | --- | --- |
| **Innovation** | A governance firewall that keeps agentic AI from controlling the lifecycle. | `src/smartgrid_mlops/agents/firewall.py` (allow/block lists, deny-by-default), `tests/test_phase17_agents.py` (firewall tests). | "What makes this different" section on the landing page; the ALLOW/BLOCK diagram in the architecture SVG; the firewall row in the dashboard. |
| **Innovation** | Honest mixed-outcome final evaluation (PV wins, LOAD/WIND lose). | `artifacts/research_tables/final_model_comparison.csv`, `reports/phase_19_completion.md`. | "Results" section on the landing page; the benchmark table in the dashboard. |
| **Technical complexity** | 20-phase system with cascade of frozen protocol artefacts. | 20 SHA-256-validated freezes under `artifacts/experimental_design/*.sha256`; 20 completion reports under `reports/`. | Architecture SVG; "Research progression" SVG; integrity baseline JSON. |
| **Technical complexity** | 13-gate promotion policy + 17-gate retraining policy, both tested. | `config/governance/phase_16_promotion_policy.yaml`, `config/retraining/phase_15_policy.yaml`, `tests/test_phase15_retraining.py`, `tests/test_phase16_*.py`. | Governance panel in the dashboard. |
| **Technical complexity** | Bounded agentic decision support with 5 specialist agents + firewall + bounded memory (no chain-of-thought). | `src/smartgrid_mlops/agents/`, `tests/test_phase17_agents.py`, `docs/research_methodology/bounded_agentic_ai.md`. | Agent firewall row in the architecture SVG. |
| **Implementation** | 231 backend tests + 18 dashboard tests, all passing. | `.venv\Scripts\python.exe -m pytest`; `tests/`. | "Test/compile status" line on the landing page; audit panel in the dashboard. |
| **Implementation** | MLflow lineage with `evidence_status` tags. | `artifacts/mlflow/`. | Audit panel in the dashboard. |
| **Impact** | Operational benefit measured by ablation, not by user study. | `reports/phase_18_completion.md` (72% effort reduction under a frozen cost model; 0 lifecycle differences; 14/14 unsafe blocked). | "What makes this different" section. |
| **Usability** | Read-only evidence interface; no training controls; accessible (skip-link, ARIA, focus styles, non-color indicators). | `dashboard/index.html`, `dashboard/styles.css`, `tests/test_phase20_dashboard.py`. | "Demo" section; click through the dashboard. |
| **Reproducibility** | Every claim in the submission is traceable to a recorded artefact. Final evaluation reproducible from a single `pytest` run. | `artifacts/ui_build/phase19_integrity_baseline.json`, `tests/`, the 20 protocol freezes with sidecar SHA-256s. | "Research evidence" + "Reproducibility" sections; the audit panel in the dashboard. |
| **Presentation** | Honest reporting of negative results; no fabricated claims; restrained research aesthetic. | `dashboard/` and `hackathon/` style + content; `docs/research_methodology/threats_to_validity.md`. | The whole submission — every section is direct. |

## Self-assessment notes

- **Innovation** is the strongest category. The agent firewall and the honest mixed-outcome reporting are both concrete and easy to verify.
- **Technical complexity** is high but the system is classical ML. A judge expecting a quantum demo will not find one; this is documented and honest.
- **Impact** is bounded — the operational benefit is measured by a cost model, not a user study. The 72% number is reproducible from the cost model constants.
- **Usability** is the area most likely to score lower than a flashy demo. The dashboard is restrained, dark-themed, and uses a tiny static asset footprint. The trade-off is honest presentation over visual polish.
- **Reproducibility** is high — 231 tests pass, 20 freezes verified, 18 dashboard tests pass, no broken links. The judge can verify the submission in minutes.
- **Presentation** is intentionally direct. The result card on the hero is the centerpiece, and the negative rows are deliberately visible. This should help credibility with technical judges.
